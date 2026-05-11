import "server-only";

import oracledb from "oracledb";
import type { GonenKukumiSearchInput } from "@/domains/gonenkukumi/schemas";
import type {
  CustomerShipBlock,
  CustomerTotalsBlock,
  DayQtySeries,
  GonenKukumiOracleResult,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";
import { withOracleReadConnection } from "@/infrastructure/oracle/with-connection";
import { ORACLE_NOT_CONFIGURED_HINT } from "@/infrastructure/oracle/pool";
import { createEmptyDayQtySeries } from "@/domains/gonenkukumi/report-grid";

const OUT_OBJECT = oracledb.OUT_FORMAT_OBJECT;

function firstDayOfSearchMonth(yearMonth: string): string {
  return `${yearMonth}/01`;
}

function addToDay(arr: DayQtySeries, ymd: string, qty: number): void {
  const m = /^(\d{4})\/(\d{2})\/(\d{2})$/.exec(String(ymd).trim());
  if (!m) return;
  const day = Number(m[3]);
  if (day < 1 || day > 31) return;
  const i = day - 1;
  arr[i] = (arr[i] ?? 0) + qty;
}

/** `yyyy/mm/dd` / `yyyy-mm-dd` 形式から日（1〜31）を取る。`Number("2026/05/06")` は NaN になるため必須 */
function dayOfMonthFromYmdLikeString(s: string): number | null {
  const t = s.replace(/\uFF0F/g, "/").trim();
  const m = /^(\d{4})[\/.\-](\d{1,2})[\/.\-](\d{1,2})/.exec(t);
  if (!m) return null;
  const dd = Number(m[3]);
  if (!Number.isFinite(dd) || dd < 1 || dd > 31) return null;
  return dd;
}

/** T_U_MONTHLY_ODR_WORK の日（DATE / 文字列・全角混在）→ 1〜31 */
function valDay(day: string | Date | null | undefined): number {
  if (day == null) return 0;
  if (day instanceof Date) {
    const n = day.getDate();
    return n >= 1 && n <= 31 ? n : 0;
  }
  let s = String(day).replace(/\u3000/g, "").replace(/日/g, "");
  s = s.replace(/[０-９]/g, (c) => {
    const code = c.charCodeAt(0);
    if (code >= 0xff10 && code <= 0xff19) return String.fromCharCode(code - 0xff10 + 0x30);
    return c;
  });
  const fromYmd = dayOfMonthFromYmdLikeString(s);
  if (fromYmd != null) return fromYmd;
  const n = Number(s.trim());
  if (!Number.isFinite(n) || n < 1 || n > 31) return 0;
  return n;
}

/** ワークの日セル（DATE / NUMBER / `yyyy/mm/dd` 文字列・全角）→ 1〜31 */
function valDayCell(raw: unknown): number {
  if (raw == null) return 0;
  if (raw instanceof Date) {
    if (!Number.isNaN(raw.getTime())) {
      const ld = raw.getDate();
      if (ld >= 1 && ld <= 31) return ld;
      const ud = raw.getUTCDate();
      if (ud >= 1 && ud <= 31) return ud;
    }
    return 0;
  }
  if (typeof raw === "number" && Number.isFinite(raw)) {
    const n = Math.trunc(raw);
    return n >= 1 && n <= 31 ? n : 0;
  }
  if (typeof raw === "bigint") {
    const n = Number(raw);
    return n >= 1 && n <= 31 ? n : 0;
  }
  return valDay(String(raw) as string);
}

/**
 * QTY_*（カンマ区切り・空白・Oracle の文字列数量）を数値化。
 * `Number("1,234")` は NaN になり JSON 化で null 落ちするため必ず正規化する。
 */
function parseMonthlyWorkQty(raw: unknown): number {
  if (raw == null) return 0;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  if (typeof raw === "bigint") return Number(raw);
  const s = String(raw)
    .replace(/\u3000/g, "")
    .replace(/,/g, "")
    .replace(/[０-９]/g, (c) => {
      const code = c.charCodeAt(0);
      if (code >= 0xff10 && code <= 0xff19) return String.fromCharCode(code - 0xff10 + 0x30);
      return c;
    })
    .trim();
  const n = Number(s);
  return Number.isFinite(n) ? n : 0;
}

/**
 * execute の行を常に列名→値の Record に揃える（行が配列＋metaData のときの吸収）。
 * node-oracledb は同一接続の並列 execute を避ける推奨があるが、行形式の揺れもここで吸収する。
 */
function normalizeExecuteRowsToRecords(r: {
  rows?: unknown[];
  metaData?: { name?: string }[];
}): Record<string, unknown>[] {
  const rawRows = r.rows ?? [];
  const meta = r.metaData;
  if (!Array.isArray(rawRows)) return [];
  return rawRows.map((row) => {
    if (Array.isArray(row) && meta && meta.length > 0) {
      const rec: Record<string, unknown> = {};
      for (let i = 0; i < meta.length && i < row.length; i++) {
        const colName = meta[i]?.name;
        if (colName) rec[colName] = row[i];
      }
      return rec;
    }
    if (row != null && typeof row === "object" && !Array.isArray(row)) {
      return { ...(row as Record<string, unknown>) };
    }
    return {};
  });
}

const DAY_COL_RE = /^DAY[_\s.-]?0*(\d{1,2})$/i;
const QTY_COL_RE = /^QTY[_\s.-]?0*(\d{1,2})$/i;

/**
 * T_U_MONTHLY_ODR_WORK の取得行を日別数量に集約（VBA NAIJI_GET2 の DAY/QTY 列走査に相当）。
 * 結果は区分「月初発注」行（`SupplierBlock.monthlyStartByDay`）にそのまま渡す。
 */
function aggregateMonthlyOdrWorkRowsToDaySeries(rows: Record<string, unknown>[]): DayQtySeries {
  const days = createEmptyDayQtySeries();
  const col = (row: Record<string, unknown>, base: string): unknown => {
    const u = row[base];
    if (u !== undefined) return u;
    const lo = row[base.toLowerCase()];
    if (lo !== undefined) return lo;
    return row[base.toUpperCase()];
  };
  for (const row of rows) {
    const dayBySlot = new Map<number, unknown>();
    const qtyBySlot = new Map<number, unknown>();
    for (const key of Object.getOwnPropertyNames(row)) {
      const nk = key.replace(/^"|"$/g, "");
      const dm = DAY_COL_RE.exec(nk);
      if (dm) {
        const slot = Number(dm[1]);
        if (slot >= 1 && slot <= 26) dayBySlot.set(slot, row[key]);
        continue;
      }
      const qm = QTY_COL_RE.exec(nk);
      if (qm) {
        const slot = Number(qm[1]);
        if (slot >= 1 && slot <= 26) qtyBySlot.set(slot, row[key]);
      }
    }
    for (let i = 1; i <= 26; i++) {
      const suf = String(i).padStart(2, "0");
      const dayRaw = dayBySlot.get(i) ?? col(row, `DAY_${suf}`);
      const qtyRaw = qtyBySlot.get(i) ?? col(row, `QTY_${suf}`);
      if (dayRaw == null && qtyRaw == null) continue;
      if (dayRaw != null && String(dayRaw).trim() === "") continue;
      const d = valDayCell(dayRaw);
      if (d === 0) continue;
      const qty = parseMonthlyWorkQty(qtyRaw);
      if (!Number.isFinite(qty)) continue;
      const idx = d - 1;
      days[idx] = (days[idx] ?? 0) + qty;
    }
  }
  for (let i = 0; i < days.length; i++) {
    const v = days[i];
    if (v != null && !Number.isFinite(v)) days[i] = null;
  }
  return days;
}

async function naisakGet(
  conn: oracledb.Connection,
  input: GonenKukumiSearchInput,
  companyCd: string | null,
): Promise<string | null> {
  const sql = `
    SELECT M_CUST_ITEM.ITEM_CD AS ITEM_CD
    FROM M_CUST_ITEM
    WHERE M_CUST_ITEM.CUST_CD = :tk
      AND M_CUST_ITEM.DLV_LOC_CD = '*'
      AND M_CUST_ITEM.CUST_ITEM_CD = :hin
      AND M_CUST_ITEM.ITEM_CD_OPTION_CHANGE_VALUE = :henk
      AND (:companyCd IS NULL OR M_CUST_ITEM.COMPANY_CD = :companyCd)
      AND M_CUST_ITEM.EFF_PHASE_IN_DATE <= TO_DATE(:asOf2, 'YYYY/MM/DD')
      AND (M_CUST_ITEM.EFF_PHASE_OUT_DATE IS NULL OR TO_DATE(:asOf, 'YYYY/MM/DD') <= M_CUST_ITEM.EFF_PHASE_OUT_DATE)`;
  const r = await conn.execute<{ ITEM_CD: string }>(
    sql,
    {
      tk: input.custCode,
      hin: input.custItem,
      henk: input.optionChange || "*",
      asOf: input.asOfDate,
      asOf2: input.asOfDate,
      companyCd,
    },
    { outFormat: OUT_OBJECT, maxRows: 1 },
  );
  const row = r.rows?.[0];
  if (!row) return null;
  return row.ITEM_CD ?? null;
}

async function fetchZaiko(conn: oracledb.Connection, itemCd: string): Promise<number> {
  const sql = `
    SELECT NVL(SUM(T_ITEM_STOCK.STOCK_ON_HAND_QTY), 0) AS "ZAIKO"
    FROM T_ITEM_STOCK
    WHERE ITEM_CD = :item`;
  const r = await conn.execute<{ ZAIKO: number }>(sql, { item: itemCd }, { outFormat: OUT_OBJECT });
  const v = r.rows?.[0]?.ZAIKO;
  return v != null ? Number(v) : 0;
}

type CustRow = {
  CUST_CD: string | number;
  CUST_ANAME: string;
  CUST_ITEM_CD: string;
  ITEM_CD: string;
};

async function fetchCustShipRows(
  conn: oracledb.Connection,
  internalItemCd: string,
  optionChange: string,
  asOfDate: string,
  companyCd: string | null,
): Promise<CustRow[]> {
  const sql = `
    SELECT
      M_CUST_ITEM.CUST_CD AS "CUST_CD",
      M_CUST.CUST_ANAME AS "CUST_ANAME",
      M_CUST_ITEM.CUST_ITEM_CD AS "CUST_ITEM_CD",
      M_CUST_ITEM.ITEM_CD AS "ITEM_CD"
    FROM M_CUST_ITEM, M_CUST
    WHERE M_CUST_ITEM.COMPANY_CD = M_CUST.COMPANY_CD
      AND M_CUST_ITEM.CUST_CD = M_CUST.CUST_CD
      AND M_CUST_ITEM.DLV_LOC_CD = '*'
      AND M_CUST_ITEM.ITEM_CD = :item
      AND M_CUST_ITEM.ITEM_CD_OPTION_CHANGE_VALUE = :henk
      AND (:companyCd IS NULL OR M_CUST_ITEM.COMPANY_CD = :companyCd)
      AND M_CUST_ITEM.EFF_PHASE_IN_DATE <= TO_DATE(:asOf2, 'YYYY/MM/DD')
      AND (M_CUST_ITEM.EFF_PHASE_OUT_DATE IS NULL OR TO_DATE(:asOf, 'YYYY/MM/DD') <= M_CUST_ITEM.EFF_PHASE_OUT_DATE)`;
  const r = await conn.execute<CustRow>(
    sql,
    {
      item: internalItemCd,
      henk: optionChange || "*",
      asOf: asOfDate,
      asOf2: asOfDate,
      companyCd,
    },
    { outFormat: OUT_OBJECT },
  );
  return (r.rows ?? []) as CustRow[];
}

async function fetchTebanAnzen(
  conn: oracledb.Connection,
  itemCd: string,
): Promise<{ teban: number; anzen: number }> {
  const sql = `
    SELECT FIXED_LT AS "FIXED_LT", SAFETY_STOCK AS "SAFETY_STOCK"
    FROM M_ITEM WHERE ITEM_CD = :item`;
  const r = await conn.execute<{ FIXED_LT: number; SAFETY_STOCK: number }>(
    sql,
    { item: itemCd },
    { outFormat: OUT_OBJECT, maxRows: 1 },
  );
  const row = r.rows?.[0];
  return {
    teban: row != null ? Number(row.FIXED_LT) : 0,
    anzen: row != null ? Number(row.SAFETY_STOCK) : 0,
  };
}

/**
 * 検索月の `yyyy/mm` を `:ym` バインドにする日別集計 SQL を、共通の
 * 「実行 → 日別配列にマージ」骨組みで呼び出すヘルパー。
 *
 * 各テーブル（T_UNCNFM_ODR / T_ODR / T_UNITE_ODR / T_SHIP / T_SALES_TEMP /
 * T_OD / T_RLSD_PUCH_ODR / T_PAST_INSPC_ACPT）の SQL は本ファイル内の定数として
 * 切り出し、薄いラッパー関数（`fetchUncnfmByDay` 等）から呼ぶ。
 */
async function fetchDayQtySeriesByMonth(
  conn: oracledb.Connection,
  args: {
    sql: string;
    binds: oracledb.BindParameters;
    dateField: string;
    qtyField: string;
  },
): Promise<DayQtySeries> {
  const days = createEmptyDayQtySeries();
  const r = await conn.execute<Record<string, unknown>>(
    args.sql,
    args.binds,
    { outFormat: OUT_OBJECT },
  );
  for (const row of r.rows ?? []) {
    addToDay(days, String(row[args.dateField] ?? ""), Number(row[args.qtyField] ?? 0));
  }
  return days;
}

const SQL_UNCNFM_BY_DAY = `
  SELECT
    TO_CHAR(UNCNFM_REQUIRED_DATE, 'yyyy/mm/dd') AS "JUDATE",
    SUM(UNCNFM_REQUIRED_QTY) AS "SURYO"
  FROM T_UNCNFM_ODR
  WHERE CUST_CD = :tk
    AND ITEM_CD = :item
    AND (:companyCd IS NULL OR COMPANY_CD = :companyCd)
    AND TO_CHAR(UNCNFM_REQUIRED_DATE, 'yyyy/mm/dd') LIKE :ym
    AND NVL(DEL_FLG, 0) = 0
  GROUP BY CUST_CD, CUST_ITEM_CD, TO_CHAR(UNCNFM_REQUIRED_DATE, 'yyyy/mm/dd'), DEL_FLG`;

async function fetchUncnfmByDay(
  conn: oracledb.Connection,
  tk: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_UNCNFM_BY_DAY,
    binds: { tk, item: itemCd, ym: `${yearMonth}%`, companyCd },
    dateField: "JUDATE",
    qtyField: "SURYO",
  });
}

/** 確定受注の前月以前残（VBA JUCHUZAN_GET — 検索月より前の納期で未完了） */
async function fetchJuchuZan(
  conn: oracledb.Connection,
  tk: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<number> {
  const ymFirst = firstDayOfSearchMonth(yearMonth);
  const sql = `
    SELECT
      SUM(T_ODR.ODR_QTY) - SUM(T_ODR.TOTAL_SHIP_QTY) AS "ZANSU"
    FROM T_ODR
    WHERE T_ODR.CUST_CD = :tk
      AND T_ODR.ITEM_CD = :item
      AND (:companyCd IS NULL OR T_ODR.COMPANY_CD = :companyCd)
      AND T_ODR.DESINATED_DLV_DATE < TO_DATE(:ymFirst, 'YYYY/MM/DD')
      AND NVL(T_ODR.ODR_CMPLT_FLG, 0) <> 1
      AND NVL(T_ODR.DEL_FLG, 0) <> 1
    GROUP BY T_ODR.CUST_CD, T_ODR.CUST_ITEM_CD`;
  const r = await conn.execute<{ ZANSU: number | null }>(
    sql,
    { tk, item: itemCd, ymFirst, companyCd },
    { outFormat: OUT_OBJECT },
  );
  let sum = 0;
  for (const row of r.rows ?? []) {
    sum += Number(row.ZANSU ?? 0);
  }
  return sum;
}

const SQL_KAKUTEI_BY_DAY = `
  SELECT
    TO_CHAR(T_ODR.DESINATED_DLV_DATE, 'yyyy/mm/dd') AS "JDATE",
    SUM(T_ODR.ODR_QTY) AS "JSURYO"
  FROM T_ODR
  WHERE T_ODR.CUST_CD = :tk
    AND T_ODR.ITEM_CD = :item
    AND (:companyCd IS NULL OR T_ODR.COMPANY_CD = :companyCd)
    AND TO_CHAR(T_ODR.DESINATED_DLV_DATE, 'yyyy/mm/dd') LIKE :ym
    AND NVL(T_ODR.DEL_FLG, 0) <> 1
  GROUP BY T_ODR.CUST_CD, T_ODR.CUST_ITEM_CD, TO_CHAR(T_ODR.DESINATED_DLV_DATE, 'yyyy/mm/dd')`;

async function fetchKakuteiByDay(
  conn: oracledb.Connection,
  tk: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_KAKUTEI_BY_DAY,
    binds: { tk, item: itemCd, ym: `${yearMonth}%`, companyCd },
    dateField: "JDATE",
    qtyField: "JSURYO",
  });
}

const SQL_TOUGOU_BY_DAY = `
  SELECT
    TO_CHAR(T_UNITE_ODR.SHIP_PLAN_DATE, 'yyyy/mm/dd') AS "JDATE",
    SUM(T_UNITE_ODR.REQUIRED_QTY) AS "JSURYO"
  FROM T_UNITE_ODR
  WHERE NVL(T_UNITE_ODR.DEL_FLG, 0) = 0
    AND (:companyCd IS NULL OR T_UNITE_ODR.COMPANY_CD = :companyCd)
    AND T_UNITE_ODR.CUST_CD = :tk
    AND T_UNITE_ODR.ITEM_CD = :item
    AND TO_CHAR(T_UNITE_ODR.SHIP_PLAN_DATE, 'yyyy/mm/dd') LIKE :ym
  GROUP BY
    T_UNITE_ODR.CUST_CD,
    T_UNITE_ODR.CUST_ITEM_CD,
    T_UNITE_ODR.ITEM_CD,
    TO_CHAR(T_UNITE_ODR.SHIP_PLAN_DATE, 'yyyy/mm/dd')`;

async function fetchTougouByDay(
  conn: oracledb.Connection,
  tk: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_TOUGOU_BY_DAY,
    binds: { tk, item: itemCd, ym: `${yearMonth}%`, companyCd },
    dateField: "JDATE",
    qtyField: "JSURYO",
  });
}

const SQL_SHIP_BY_DAY = `
  SELECT
    TO_CHAR(T_SHIP.SHIP_DATE, 'yyyy/mm/dd') AS "SDATE",
    SUM(T_SHIP.SHIP_QTY) AS "SSURYO"
  FROM T_SHIP
  WHERE T_SHIP.CUST_CD = :tk
    AND T_SHIP.ITEM_CD = :item
    AND (:companyCd IS NULL OR T_SHIP.COMPANY_CD = :companyCd)
    AND TO_CHAR(T_SHIP.SHIP_DATE, 'yyyy/mm/dd') LIKE :ym
    AND NVL(T_SHIP.DEL_FLG, 0) <> 1
  GROUP BY
    T_SHIP.CUST_CD,
    T_SHIP.CUST_ITEM_CD,
    T_SHIP.ITEM_CD,
    TO_CHAR(T_SHIP.SHIP_DATE, 'yyyy/mm/dd')`;

async function fetchShipByDay(
  conn: oracledb.Connection,
  tk: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_SHIP_BY_DAY,
    binds: { tk, item: itemCd, ym: `${yearMonth}%`, companyCd },
    dateField: "SDATE",
    qtyField: "SSURYO",
  });
}

const SQL_SALES_BY_DAY = `
  SELECT
    TO_CHAR(T_SALES_TEMP.SALES_DATE, 'yyyy/mm/dd') AS "SDATE",
    SUM(T_SALES_TEMP.SALES_QTY) AS "USURYO"
  FROM T_SALES_TEMP
  WHERE T_SALES_TEMP.CUST_CD = :tk
    AND T_SALES_TEMP.ITEM_CD = :item
    AND (:companyCd IS NULL OR T_SALES_TEMP.COMPANY_CD = :companyCd)
    AND TO_CHAR(T_SALES_TEMP.SALES_DATE, 'yyyy/mm/dd') LIKE :ym
    AND NVL(T_SALES_TEMP.DEL_FLG, 0) <> 1
    AND NVL(T_SALES_TEMP.ONEROUS_CONS_SALES_TYP, 0) <> 1
  GROUP BY
    T_SALES_TEMP.CUST_CD,
    T_SALES_TEMP.ITEM_CD,
    TO_CHAR(T_SALES_TEMP.SALES_DATE, 'yyyy/mm/dd')`;

async function fetchSalesByDay(
  conn: oracledb.Connection,
  tk: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_SALES_BY_DAY,
    binds: { tk, item: itemCd, ym: `${yearMonth}%`, companyCd },
    dateField: "SDATE",
    qtyField: "USURYO",
  });
}

type BomRow = { COMP_ITEM_CD: string; KAISO: number; CONS_TYP: number | null };

async function fetchBomComponents(
  conn: oracledb.Connection,
  parentItemCd: string,
  asOfDate: string,
): Promise<BomRow[]> {
  const sql = `
    SELECT
      ps1.COMP_ITEM_CD AS "COMP_ITEM_CD",
      ps1.CONS_TYP AS "CONS_TYP",
      LEVEL AS "KAISO"
    FROM (
      SELECT *
      FROM M_PS
      WHERE TO_DATE(:asOf, 'YYYY/MM/DD') <= EFF_PHASE_OUT_DATE
        AND EFF_PHASE_IN_DATE <= TO_DATE(:asOf2, 'YYYY/MM/DD')
    ) ps1
    START WITH ps1.PARENT_ITEM_CD = :parent
    CONNECT BY PRIOR ps1.COMP_ITEM_CD = ps1.PARENT_ITEM_CD`;
  const r = await conn.execute<BomRow>(
    sql,
    { asOf: asOfDate, asOf2: asOfDate, parent: parentItemCd },
    { outFormat: OUT_OBJECT },
  );
  return (r.rows ?? []) as BomRow[];
}

type ItemProcRow = {
  FIXED_LT: number;
  SAFETY_STOCK: number;
  OUTSIDE_TYP: string;
  PROCESS_REQUEST_ISS_TYP: string | null;
  KANBAN_FLG: string | null;
};

async function fetchItemProc(conn: oracledb.Connection, itemCd: string): Promise<ItemProcRow | null> {
  const sql = `
    SELECT FIXED_LT AS "FIXED_LT",
           SAFETY_STOCK AS "SAFETY_STOCK",
           TRIM(OUTSIDE_TYP) AS "OUTSIDE_TYP",
           PROCESS_REQUEST_ISS_TYP AS "PROCESS_REQUEST_ISS_TYP",
           KANBAN_FLG AS "KANBAN_FLG"
    FROM M_ITEM
    WHERE ITEM_CD = :item`;
  const r = await conn.execute<ItemProcRow>(sql, { item: itemCd }, { outFormat: OUT_OBJECT, maxRows: 1 });
  return (r.rows?.[0] as ItemProcRow | undefined) ?? null;
}

function arrangementLabel(row: ItemProcRow): string {
  // DB 側が NUMBER の場合、node-oracledb が number で返すことがあるため文字列化して判定する
  const proc = String(row.PROCESS_REQUEST_ISS_TYP ?? "").trim();
  const kanban = String(row.KANBAN_FLG ?? "").trim();
  if (proc === "1") return "加工依頼";
  if (kanban === "1") return "かんばん";
  return "";
}

type VendorRow = {
  SICODE: string;
  SINAME: string;
  ITEM: string;
  HOKANKU: string;
};

async function fetchVendorForItem(
  conn: oracledb.Connection,
  itemCd: string,
  companyCd: string | null,
): Promise<VendorRow | null> {
  const sql = `
    SELECT * FROM (
      SELECT
        M_PUCH_UNIT_COST_H.VEND_CD AS "SICODE",
        M_VEND_CTRL.VEND_ANAME AS "SINAME",
        M_PUCH_UNIT_COST_H.ITEM_CD AS "ITEM",
        NVL(M_ITEM_RCV_WH.WH_CD, '？') AS "HOKANKU"
      FROM (M_PUCH_UNIT_COST_H
        LEFT JOIN M_VEND_CTRL
          ON M_PUCH_UNIT_COST_H.COMPANY_CD = M_VEND_CTRL.COMPANY_CD
         AND M_PUCH_UNIT_COST_H.VEND_CD = M_VEND_CTRL.VEND_CD)
        LEFT JOIN M_ITEM_RCV_WH ON M_PUCH_UNIT_COST_H.ITEM_CD = M_ITEM_RCV_WH.ITEM_CD
      WHERE M_PUCH_UNIT_COST_H.ITEM_CD = :item
        AND (:companyCd IS NULL OR M_PUCH_UNIT_COST_H.COMPANY_CD = :companyCd)
      ORDER BY M_PUCH_UNIT_COST_H.PUCH_PRIORITY_REF_NO ASC, M_PUCH_UNIT_COST_H.VEND_CD ASC
    ) WHERE ROWNUM = 1`;
  const r = await conn.execute<VendorRow>(
    sql,
    { item: itemCd, companyCd },
    { outFormat: OUT_OBJECT, maxRows: 1 },
  );
  return (r.rows?.[0] as VendorRow | undefined) ?? null;
}

async function fetchMonthlyStartByDay(
  conn: oracledb.Connection,
  vendCd: string,
  arrivalItemCd: string,
  yearMonth: string,
): Promise<DayQtySeries> {
  const ym = /^(\d{4})\/(\d{2})$/.exec(yearMonth.trim());
  const yNum = ym ? Number(ym[1]) : Number(yearMonth.slice(0, 4));
  const mNum = ym ? Number(ym[2]) : Number(yearMonth.slice(5, 7));
  /* DDL: MNGMNT_YEAR / MNGMNT_MONTH は NUMBER。VARCHAR2 の VENDOR_CD / ARRIVAL_ITEM_CD は空白差を TRIM で吸収 */
  const vStr = vendCd.trim();
  const iStr = arrivalItemCd.trim();
  const sql = `
    SELECT MNGMNT_YEAR AS "Y", MNGMNT_MONTH AS "M",
      DAY_01, QTY_01, DAY_02, QTY_02, DAY_03, QTY_03, DAY_04, QTY_04,
      DAY_05, QTY_05, DAY_06, QTY_06, DAY_07, QTY_07, DAY_08, QTY_08,
      DAY_09, QTY_09, DAY_10, QTY_10, DAY_11, QTY_11, DAY_12, QTY_12,
      DAY_13, QTY_13, DAY_14, QTY_14, DAY_15, QTY_15, DAY_16, QTY_16,
      DAY_17, QTY_17, DAY_18, QTY_18, DAY_19, QTY_19, DAY_20, QTY_20,
      DAY_21, QTY_21, DAY_22, QTY_22, DAY_23, QTY_23, DAY_24, QTY_24,
      DAY_25, QTY_25, DAY_26, QTY_26
    FROM T_U_MONTHLY_ODR_WORK
    WHERE MNGMNT_YEAR = :yNum
      AND MNGMNT_MONTH = :mNum
      AND TRIM(VENDOR_CD) = :vStr
      AND TRIM(ARRIVAL_ITEM_CD) = :iStr`;
  const r = await conn.execute<Record<string, unknown>>(
    sql,
    { yNum, mNum, vStr, iStr },
    { outFormat: OUT_OBJECT },
  );
  const rows = normalizeExecuteRowsToRecords(r);
  /** 区分「月初発注」＝ `SupplierBlock.monthlyStartByDay` へそのまま渡す日別系列 */
  return aggregateMonthlyOdrWorkRowsToDaySeries(rows);
}

const SQL_DEMAND_BY_DAY = `
  SELECT
    TO_CHAR(T_OD.PRD_DUE_DATE, 'yyyy/mm/dd') AS "KDATE",
    SUM(T_OD.ODR_QTY) AS "ODR"
  FROM T_OD T_OD
  LEFT OUTER JOIN T_RLSD_PUCH_ODR ON T_OD.OD_NO = T_RLSD_PUCH_ODR.OD_NO
  WHERE T_OD.ITEM_CD = :item
    AND TO_CHAR(T_OD.PRD_DUE_DATE, 'yyyy/mm/dd') LIKE :ym
    AND T_OD.OD_TYP = 2
    AND (T_RLSD_PUCH_ODR.PUCH_ODR_CD IS NULL OR NVL(T_RLSD_PUCH_ODR.ODR_CANCEL_SLIP_ISS_FLG, 0) = 0)
  GROUP BY T_OD.ITEM_CD, T_OD.OD_TYP, TO_CHAR(T_OD.PRD_DUE_DATE, 'yyyy/mm/dd')`;

async function fetchDemandByDay(
  conn: oracledb.Connection,
  itemCd: string,
  yearMonth: string,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_DEMAND_BY_DAY,
    binds: { item: itemCd, ym: `${yearMonth}%` },
    dateField: "KDATE",
    qtyField: "ODR",
  });
}

async function fetchChuzan(
  conn: oracledb.Connection,
  vendCd: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<number> {
  const ymFirst = firstDayOfSearchMonth(yearMonth);
  const sql = `
    SELECT
      MAX(T_RLSD_PUCH_ODR.PUCH_ODR_QTY) AS "HCSURYO",
      NVL(SUM(T_PAST_INSPC_ACPT.ACPT_QTY), 0) AS "NYSURYO",
      MAX(T_RLSD_PUCH_ODR.PUCH_ODR_QTY) - NVL(SUM(T_PAST_INSPC_ACPT.ACPT_QTY), 0) AS "ZANSU"
    FROM T_RLSD_PUCH_ODR
    LEFT OUTER JOIN T_PAST_INSPC_ACPT
      ON T_RLSD_PUCH_ODR.PUCH_ODR_CD = T_PAST_INSPC_ACPT.PUCH_ODR_CD
    WHERE T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE < TO_DATE(:ymFirst, 'YYYY/MM/DD')
      AND (:companyCd IS NULL OR T_RLSD_PUCH_ODR.COMPANY_CD = :companyCd)
      AND T_RLSD_PUCH_ODR.VEND_CD = :vend
      AND T_RLSD_PUCH_ODR.ITEM_CD = :item
      AND T_RLSD_PUCH_ODR.PUCH_ODR_STS_TYP = 2
      AND NVL(T_RLSD_PUCH_ODR.ODR_CANCEL_SLIP_ISS_FLG, 0) = 0
    GROUP BY T_RLSD_PUCH_ODR.PUCH_ODR_CD, T_RLSD_PUCH_ODR.VEND_CD, T_RLSD_PUCH_ODR.ITEM_CD`;
  const r = await conn.execute<{ ZANSU: number }>(
    sql,
    { vend: vendCd, item: itemCd, ymFirst, companyCd },
    { outFormat: OUT_OBJECT },
  );
  let total = 0;
  for (const row of r.rows ?? []) {
    total += Number(row.ZANSU ?? 0);
  }
  return total;
}

const SQL_KAKUTEI_PUCH_BY_DAY = `
  SELECT
    TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE, 'yyyy/mm/dd') AS "HDATE",
    SUM(T_RLSD_PUCH_ODR.PUCH_ODR_QTY) AS "HSURYO"
  FROM T_RLSD_PUCH_ODR
  WHERE T_RLSD_PUCH_ODR.VEND_CD = :vend
    AND T_RLSD_PUCH_ODR.ITEM_CD = :item
    AND (:companyCd IS NULL OR T_RLSD_PUCH_ODR.COMPANY_CD = :companyCd)
    AND TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE, 'yyyy/mm/dd') LIKE :ym
    AND NVL(T_RLSD_PUCH_ODR.PUCH_ODR_STS_TYP, 0) <> 1
    AND NVL(T_RLSD_PUCH_ODR.ODR_CANCEL_SLIP_ISS_FLG, 0) = 0
  GROUP BY
    T_RLSD_PUCH_ODR.VEND_CD,
    T_RLSD_PUCH_ODR.ITEM_CD,
    TO_CHAR(T_RLSD_PUCH_ODR.PUCH_ODR_DLV_DATE, 'yyyy/mm/dd')`;

async function fetchKakuteiPuchByDay(
  conn: oracledb.Connection,
  vendCd: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_KAKUTEI_PUCH_BY_DAY,
    binds: { vend: vendCd, item: itemCd, ym: `${yearMonth}%`, companyCd },
    dateField: "HDATE",
    qtyField: "HSURYO",
  });
}

const SQL_RECEIPT_BY_DAY = `
  SELECT
    TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE, 'yyyy/mm/dd') AS "NYDATE",
    SUM(T_PAST_INSPC_ACPT.INSPC_ACPT_QTY) AS "NSURYO"
  FROM T_PAST_INSPC_ACPT
  WHERE T_PAST_INSPC_ACPT.VEND_CD = :vend
    AND T_PAST_INSPC_ACPT.ITEM_CD = :item
    AND (:companyCd IS NULL OR T_PAST_INSPC_ACPT.COMPANY_CD = :companyCd)
    AND TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE, 'yyyy/mm/dd') LIKE :ym
  GROUP BY
    T_PAST_INSPC_ACPT.VEND_CD,
    T_PAST_INSPC_ACPT.ITEM_CD,
    TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE, 'yyyy/mm/dd')
  ORDER BY TO_CHAR(T_PAST_INSPC_ACPT.ACPT_DATE, 'yyyy/mm/dd')`;

async function fetchReceiptByDay(
  conn: oracledb.Connection,
  vendCd: string,
  itemCd: string,
  yearMonth: string,
  companyCd: string | null,
): Promise<DayQtySeries> {
  return fetchDayQtySeriesByMonth(conn, {
    sql: SQL_RECEIPT_BY_DAY,
    binds: { vend: vendCd, item: itemCd, ym: `${yearMonth}%`, companyCd },
    dateField: "NYDATE",
    qtyField: "NSURYO",
  });
}

function sumSeries(a: DayQtySeries, b: DayQtySeries): DayQtySeries {
  return a.map((v, i) => {
    const x = v ?? 0;
    const y = b[i] ?? 0;
    if (x === 0 && y === 0) return null;
    return x + y;
  });
}

/** M_CAL の休日フラグが立っている日（日にち 1〜31） */
async function fetchHolidayDays(
  conn: oracledb.Connection,
  yearMonth: string,
): Promise<number[]> {
  /*
   * ORA-01722 回避: CAL_DATE が NUMBER(YYYYMMDD) のとき TO_CHAR(数値, 'YYYY/MM') を使わない。
   * 月の絞り込み・日の桁取りは VBA CALEN_SET（M_CAL.CAL_DATE LIKE KANRYM & "%"、Mid(CAL_DATE,9,2)）に合わせる。
   * 休日: VBA は HOLIDAY_FLG = "0" のときだけ平日色。Null = "0" は Null で If は False → 休日色なので、
   * SQL でも「Trim 後が '0' 以外、またはフラグが Null」を休日とする。
   */
  const ymCompact = yearMonth.replace(/\//g, "");
  const ymDash = yearMonth.replace(/\//g, "-");
  const sql = `
    WITH cal AS (
      SELECT TRIM(CAST(M_CAL.CAL_DATE AS VARCHAR2(32))) AS ds
      FROM M_CAL
      WHERE (TRIM(M_CAL.HOLIDAY_FLG || '') IS NULL OR TRIM(M_CAL.HOLIDAY_FLG || '') <> '0')
    )
    SELECT CASE
      WHEN REGEXP_LIKE(cal.ds, '^[0-9]{8}$') THEN SUBSTR(cal.ds, 7, 2)
      WHEN REGEXP_LIKE(cal.ds, '^[0-9]{4}/[0-9]{2}/[0-9]{2}$') THEN SUBSTR(cal.ds, 9, 2)
      WHEN REGEXP_LIKE(cal.ds, '^[0-9]{4}-[0-9]{2}-[0-9]{2}') THEN SUBSTR(cal.ds, 9, 2)
      ELSE NULL
    END AS DDAY
    FROM cal
    WHERE (
        (REGEXP_LIKE(cal.ds, '^[0-9]{8}$') AND SUBSTR(cal.ds, 1, 6) = :ymCompact)
        OR (REGEXP_LIKE(cal.ds, '^[0-9]{4}/[0-9]{2}/[0-9]{2}$') AND SUBSTR(cal.ds, 1, 7) = :ymSlash)
        OR (REGEXP_LIKE(cal.ds, '^[0-9]{4}-[0-9]{2}-[0-9]{2}') AND SUBSTR(cal.ds, 1, 7) = :ymDash)
      )
    ORDER BY cal.ds`;
  try {
    const r = await conn.execute<{ DDAY: string | null }>(
      sql,
      { ymCompact, ymSlash: yearMonth, ymDash },
      { outFormat: OUT_OBJECT },
    );
    const out: number[] = [];
    for (const row of r.rows ?? []) {
      const raw = row.DDAY;
      if (raw == null || String(raw).trim() === "") continue;
      const d = parseInt(String(raw).trim(), 10);
      if (Number.isFinite(d) && d >= 1 && d <= 31) out.push(d);
    }
    return out;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.warn("[gonenkukumi] M_CAL 休日取得に失敗したため休日色なしで続行:", msg);
    return [];
  }
}

function buildCustomerTotals(blocks: CustomerShipBlock[]): CustomerTotalsBlock {
  let u = createEmptyDayQtySeries();
  let k = createEmptyDayQtySeries();
  let t = createEmptyDayQtySeries();
  let s = createEmptyDayQtySeries();
  let sa = createEmptyDayQtySeries();
  for (const b of blocks) {
    u = sumSeries(u, b.uncnfmByDay);
    k = sumSeries(k, b.confirmedOrderByDay);
    t = sumSeries(t, b.uniteOrderByDay);
    s = sumSeries(s, b.shipByDay);
    sa = sumSeries(sa, b.salesByDay);
  }
  return {
    uncnfmByDay: u,
    confirmedOrderByDay: k,
    uniteOrderByDay: t,
    shipByDay: s,
    salesByDay: sa,
  };
}

export async function runGonenKukumiOracleSearch(
  input: GonenKukumiSearchInput,
): Promise<GonenKukumiOracleResult> {
  const notConfigured: GonenKukumiOracleResult = {
    ok: false,
    code: "ORACLE_NOT_CONFIGURED",
    message: ORACLE_NOT_CONFIGURED_HINT,
  };

  try {
    return await withOracleReadConnection<GonenKukumiOracleResult>(notConfigured, async (conn, { companyCd }) => {
    const internalItemCd = await naisakGet(conn, input, companyCd);
    if (!internalItemCd) {
      return { ok: false, code: "NAISAK_NOT_FOUND", message: "内作品目が見つかりません" };
    }

    const [custRows, holidayDays] = await Promise.all([
      fetchCustShipRows(conn, internalItemCd, input.optionChange, input.asOfDate, companyCd),
      fetchHolidayDays(conn, input.yearMonth),
    ]);
    const { teban, anzen } = await fetchTebanAnzen(conn, internalItemCd);
    const zaikoMain = await fetchZaiko(conn, internalItemCd);

    const customerBlocks: CustomerShipBlock[] = [];
    for (const row of custRows) {
      const tk = String(row.CUST_CD);
      const [
        uncnfmByDay,
        confirmedOrderPrevBalance,
        confirmedOrderByDay,
        uniteOrderByDay,
        shipByDay,
        salesByDay,
      ] = await Promise.all([
        fetchUncnfmByDay(conn, tk, internalItemCd, input.yearMonth, companyCd),
        fetchJuchuZan(conn, tk, internalItemCd, input.yearMonth, companyCd),
        fetchKakuteiByDay(conn, tk, internalItemCd, input.yearMonth, companyCd),
        fetchTougouByDay(conn, tk, internalItemCd, input.yearMonth, companyCd),
        fetchShipByDay(conn, tk, internalItemCd, input.yearMonth, companyCd),
        fetchSalesByDay(conn, tk, internalItemCd, input.yearMonth, companyCd),
      ]);
      customerBlocks.push({
        custCode: tk,
        custName: row.CUST_ANAME != null ? String(row.CUST_ANAME).trim() : "",
        custItemCd: row.CUST_ITEM_CD != null ? String(row.CUST_ITEM_CD).trim() : "",
        teban,
        anzen,
        zaiko: zaikoMain,
        uncnfmByDay,
        confirmedOrderPrevBalance,
        confirmedOrderByDay,
        uniteOrderByDay,
        shipByDay,
        salesByDay,
      });
    }

    if (customerBlocks.length === 0) {
      const uncnfmByDay = await fetchUncnfmByDay(
        conn,
        input.custCode,
        internalItemCd,
        input.yearMonth,
        companyCd,
      );
      customerBlocks.push({
        custCode: input.custCode,
        custName: "",
        custItemCd: input.custItem,
        teban,
        anzen,
        zaiko: zaikoMain,
        uncnfmByDay,
        confirmedOrderPrevBalance: await fetchJuchuZan(
          conn,
          input.custCode,
          internalItemCd,
          input.yearMonth,
          companyCd,
        ),
        confirmedOrderByDay: await fetchKakuteiByDay(
          conn,
          input.custCode,
          internalItemCd,
          input.yearMonth,
          companyCd,
        ),
        uniteOrderByDay: await fetchTougouByDay(
          conn,
          input.custCode,
          internalItemCd,
          input.yearMonth,
          companyCd,
        ),
        shipByDay: await fetchShipByDay(conn, input.custCode, internalItemCd, input.yearMonth, companyCd),
        salesByDay: await fetchSalesByDay(conn, input.custCode, internalItemCd, input.yearMonth, companyCd),
      });
    }

    const customerTotals = customerBlocks.length > 1 ? buildCustomerTotals(customerBlocks) : null;

    const bomRows = await fetchBomComponents(conn, internalItemCd, input.asOfDate);
    const seenComp = new Set<string>();
    const supplierBlocks: SupplierBlock[] = [];

    for (const bom of bomRows) {
      const comp = String(bom.COMP_ITEM_CD).trim();
      if (!comp || seenComp.has(comp)) continue;
      seenComp.add(comp);

      const itemRow = await fetchItemProc(conn, comp);
      if (!itemRow || String(itemRow.OUTSIDE_TYP).trim() !== "2") continue;

      const vend = await fetchVendorForItem(conn, comp, companyCd);
      if (!vend) continue;

      const arrangementTyp = arrangementLabel(itemRow);
      const whCd = String(vend.HOKANKU ?? "？");

      /* 同一 Connection 上の並列 execute は避ける（node-oracledb 推奨・結果取り違え防止） */
      const monthlyStartByDay = await fetchMonthlyStartByDay(conn, String(vend.SICODE), comp, input.yearMonth);
      const demandByDay = await fetchDemandByDay(conn, comp, input.yearMonth);
      const confirmedPuchPrevBalance = await fetchChuzan(
        conn,
        String(vend.SICODE),
        comp,
        input.yearMonth,
        companyCd,
      );
      const confirmedPuchByDay = await fetchKakuteiPuchByDay(
        conn,
        String(vend.SICODE),
        comp,
        input.yearMonth,
        companyCd,
      );
      const receiptByDay = await fetchReceiptByDay(
        conn,
        String(vend.SICODE),
        comp,
        input.yearMonth,
        companyCd,
      );
      const zaiko = await fetchZaiko(conn, comp);

      supplierBlocks.push({
        vendCode: String(vend.SICODE),
        vendName: String(vend.SINAME ?? ""),
        itemCdWithLevel: `${comp} (${bom.KAISO})`,
        kaiso: Number(bom.KAISO),
        arrangementTyp,
        whCd,
        consTyp: Number(bom.CONS_TYP ?? 0),
        topItemCd: internalItemCd,
        teban: Number(itemRow.FIXED_LT),
        anzen: Number(itemRow.SAFETY_STOCK),
        zaiko,
        monthlyStartByDay,
        demandByDay,
        confirmedPuchPrevBalance,
        confirmedPuchByDay,
        receiptByDay,
      });
    }

    return {
      ok: true,
      internalItemCd,
      holidayDays,
      customerBlocks,
      customerTotals,
      supplierBlocks,
    };
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return {
      ok: false,
      code: "ORACLE_ERROR",
      message: `Oracle エラー: ${msg}`,
    };
  }
}
