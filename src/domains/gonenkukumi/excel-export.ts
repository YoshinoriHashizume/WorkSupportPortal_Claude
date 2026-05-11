import ExcelJS from "exceljs";
import { GONENKUKUMI_EXCEL_FONT_NAME } from "@/domains/gonenkukumi/ms-gothic";
import { kaisoColor } from "@/domains/gonenkukumi/kaiso-color";
import { groupSegmentsFromCache } from "@/domains/gonenkukumi/panel-segments";
import {
  daysInMonthYm,
  GONEN_FIXED_GRID_BORDER_EXCEL_ARGB,
  GONEN_PAD_DAY_EXCEL_ARGB,
  GONEN_REPORT_GRID_DAYS,
} from "@/domains/gonenkukumi/report-grid";
import { compareGonenKukumiYearMonth, normalizeYearMonth } from "@/domains/gonenkukumi/year-month-nav";
import type {
  CustomerShipBlock,
  DayQtySeries,
  GonenKukumiOracleSuccess,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";
import {
  findCustomerBlock,
  findSupplierBlock,
} from "@/domains/gonenkukumi/block-finders";
import {
  gonenSegmentKaisoIndex,
  gonenSupplierBlockKaisoIndex,
} from "@/domains/gonenkukumi/segment-theme";
import {
  customerBannerLine,
  supplierBannerLine,
} from "@/domains/gonenkukumi/block-banner-fields";
import {
  resolveCustomerRows,
  resolveSupplierRows,
} from "@/domains/gonenkukumi/block-rows";

export type GonenExcelExportParams = {
  custCode: string;
  custItem: string;
  optionChange: string;
  yearMonth: string;
  asOfDate: string;
};

/** 表セル用：0 と null/undefined は空欄 */
function excelQty(v: number | null | undefined): number | string {
  if (v == null || v === 0) return "";
  return v;
}

function dayHeaders(maxDay: number): string[] {
  return Array.from({ length: maxDay }, (_, i) => `${i + 1}日`);
}

/** 休日列のみに塗りを適用する（活性日のみ）。 */
function applyDayColumnFillsToRange(
  ws: ExcelJS.Worksheet,
  rowStart: number,
  rowEnd: number,
  activeDays: number,
  holidays: ReadonlySet<number>,
  holidayFill: ExcelJS.Fill,
) {
  const n = Math.min(activeDays, GONEN_REPORT_GRID_DAYS);
  for (let row = rowStart; row <= rowEnd; row++) {
    for (let day = 1; day <= n; day++) {
      if (!holidays.has(day)) continue;
      ws.getCell(row, 3 + day).fill = holidayFill;
    }
  }
}

function applyPadDayColumnFills(ws: ExcelJS.Worksheet, rowStart: number, rowEnd: number, activeDays: number) {
  const padFill: ExcelJS.Fill = { type: "pattern", pattern: "solid", fgColor: { argb: GONEN_PAD_DAY_EXCEL_ARGB } };
  const padEdge: ExcelJS.Border = { style: "thin", color: { argb: GONEN_PAD_DAY_EXCEL_ARGB } };
  const padBorder: Partial<ExcelJS.Borders> = { top: padEdge, left: padEdge, bottom: padEdge, right: padEdge };
  for (let row = rowStart; row <= rowEnd; row++) {
    for (let day = activeDays + 1; day <= GONEN_REPORT_GRID_DAYS; day++) {
      const cell = ws.getCell(row, 3 + day);
      cell.fill = padFill;
      // 未使用日列は罫線も背景と同色にして「空欄」に見せる（Web と同様）
      cell.border = padBorder as ExcelJS.Borders;
      cell.value = "";
    }
  }
}

/** 一覧エリアの数値セルに千桁区切り（#,##0）を付与 */
function applyThousandSeparatorToTableNumbers(
  ws: ExcelJS.Worksheet,
  headerRow: number,
  lastRow: number,
  lastCol: number,
) {
  const numFmt = "#,##0";
  for (let r = headerRow + 1; r <= lastRow; r++) {
    for (let c = 2; c <= lastCol; c++) {
      const cell = ws.getCell(r, c);
      const v = cell.value;
      if (typeof v === "number" && Number.isFinite(v)) {
        cell.numFmt = numFmt;
      }
    }
  }
}

function dayValues31Active(series: DayQtySeries, activeDays: number): (number | string)[] {
  return Array.from({ length: GONEN_REPORT_GRID_DAYS }, (_, i) => (i + 1 > activeDays ? "" : excelQty(series[i])));
}

function lastColIndexFixed(): number {
  return 3 + GONEN_REPORT_GRID_DAYS;
}

function padRow(cells: (string | number)[], lastCol: number): (string | number)[] {
  const out = [...cells];
  while (out.length < lastCol) out.push("");
  return out.slice(0, lastCol);
}

/**
 * 結合セルはマスタのみに枠を付与する（スレーブへ代入しても Excel 上で外周が欠けることがある）。
 * 未結合セルは従来どおり 1 セル単位で四辺つきの細線にする。
 */
function applyThinBordersMergeAware(
  ws: ExcelJS.Worksheet,
  top: number,
  bottom: number,
  lastCol: number,
  colorArgb: string,
) {
  const edge = { style: "thin" as const, color: { argb: colorArgb } };
  const full = { top: edge, left: edge, bottom: edge, right: edge } as ExcelJS.Borders;
  for (let r = top; r <= bottom; r++) {
    for (let c = 1; c <= lastCol; c++) {
      const cell = ws.getCell(r, c);
      if (cell.master.address !== cell.address) {
        continue;
      }
      cell.border = full;
    }
  }
}

/** 1 行に四辺つきの細線。結合行はマスタのみ（見出し行の外周が欠けないようにする） */
function applyFullBorderToRowMergeAware(
  ws: ExcelJS.Worksheet,
  row: number,
  lastCol: number,
  colorArgb: string,
) {
  const edge = { style: "thin" as const, color: { argb: colorArgb } };
  const full = { top: edge, left: edge, bottom: edge, right: edge } as ExcelJS.Borders;
  const c1 = ws.getCell(row, 1);
  if (c1.isMerged) {
    c1.master.border = full;
    return;
  }
  for (let c = 1; c <= lastCol; c++) {
    ws.getCell(row, c).border = full;
  }
}

function applyOutlineBorder(
  ws: ExcelJS.Worksheet,
  top: number,
  left: number,
  bottom: number,
  right: number,
  colorArgb: string,
) {
  const edge: ExcelJS.Border = { style: "thin", color: { argb: colorArgb } };
  for (let r = top; r <= bottom; r++) {
    for (let c = left; c <= right; c++) {
      const cell = ws.getCell(r, c);
      const prev = (cell.border ?? {}) as Partial<ExcelJS.Borders>;
      const next: Partial<ExcelJS.Borders> = { ...prev };
      if (r === top) next.top = edge;
      if (r === bottom) next.bottom = edge;
      if (c === left) next.left = edge;
      if (c === right) next.right = edge;
      cell.border = next as ExcelJS.Borders;
    }
  }
}

type SectionTheme = {
  baseFill: ExcelJS.Fill;
  veryLightFill: ExcelJS.Fill;
  outerBorderArgb: string;
  titleBorderArgb: string;
};

function sectionTheme(index: number): SectionTheme {
  const k = kaisoColor(index);
  return {
    baseFill: { type: "pattern", pattern: "solid", fgColor: { argb: k.excelArgbBg } },
    veryLightFill: { type: "pattern", pattern: "solid", fgColor: { argb: k.excelArgbVeryLightBg } },
    outerBorderArgb: k.excelArgbOuterBorder,
    titleBorderArgb: k.excelArgbBorder,
  };
}

/** シート使用範囲の全セルに MS ゴシック（Excel 名: MS Gothic）を付与（既存の太字・サイズ・書式は維持） */
function applyMsGothicToUsedRange(ws: ExcelJS.Worksheet, lastCol: number, lastRow: number) {
  for (let r = 1; r <= lastRow; r++) {
    for (let c = 1; c <= lastCol; c++) {
      const cell = ws.getCell(r, c);
      const prev = (cell.font ?? {}) as Partial<ExcelJS.Font>;
      cell.font = { ...prev, name: GONENKUKUMI_EXCEL_FONT_NAME };
    }
  }
}

/** 検索条件ブロックの D 列以降のみ塗りを消す（一覧の日付・休日色を消さないため） */
function clearCondBlockDayColumnFills(
  ws: ExcelJS.Worksheet,
  condTop: number,
  condBottom: number,
  lastCol: number,
) {
  const noFill: ExcelJS.Fill = { type: "pattern", pattern: "none" };
  for (let r = condTop; r <= condBottom; r++) {
    for (let c = 4; c <= lastCol; c++) {
      const cell = ws.getCell(r, c);
      if (cell.isMerged && cell.master.address !== cell.address) continue;
      cell.fill = noFill;
    }
  }
}

function styleSupplierKaisoHeaderRow(
  ws: ExcelJS.Worksheet,
  row: number,
  lastCol: number,
  activeDays: number,
  baseFill: ExcelJS.Fill,
) {
  const padFill: ExcelJS.Fill = { type: "pattern", pattern: "solid", fgColor: { argb: GONEN_PAD_DAY_EXCEL_ARGB } };
  for (let c = 1; c <= lastCol; c++) {
    const cell = ws.getCell(row, c);
    cell.font = { bold: true };
    if (c >= 4) {
      const day = c - 3;
      if (day > activeDays) {
        cell.fill = padFill;
        // 未使用日（例: 4/31）の見出し文字は表示しない
        cell.value = "";
      } else {
        cell.fill = baseFill;
      }
    } else {
      cell.fill = baseFill;
    }
    cell.alignment = { vertical: "middle", horizontal: c >= 2 ? "right" : "left" };
  }
  for (let day = 1; day <= GONEN_REPORT_GRID_DAYS; day++) {
    const c = 3 + day;
    ws.getCell(row, c).alignment = { vertical: "middle", horizontal: "right" };
  }
}

const COND_KEY_FILL = {
  type: "pattern" as const,
  pattern: "solid" as const,
  fgColor: { argb: GONEN_FIXED_GRID_BORDER_EXCEL_ARGB },
};

/** 検索条件・ブロック見出しで共通: 表題行（太字・グレー背景） */
function styleCondKeyRow(ws: ExcelJS.Worksheet, row: number, lastCol: number) {
  for (let c = 1; c <= lastCol; c++) {
    const cell = ws.getCell(row, c);
    cell.font = { bold: true };
    cell.fill = COND_KEY_FILL;
    cell.alignment = { vertical: "middle", horizontal: "left" };
  }
}

/** ブロック先頭のメタ情報を 1 行・全列結合で出力（背景は休日列と同系色） */
function appendMergedMetaRow(
  ws: ExcelJS.Worksheet,
  text: string,
  lastCol: number,
  sectionTitleFill: ExcelJS.Fill,
  borderArgb: string = GONEN_FIXED_GRID_BORDER_EXCEL_ARGB,
  onMergedRow?: (row: number, borderArgb: string) => void,
) {
  const r0 = ws.rowCount + 1;
  ws.addRow(padRow([text], lastCol));
  ws.mergeCells(r0, 1, r0, lastCol);
  ws.getCell(r0, 1).value = text;
  const edge = { style: "thin" as const, color: { argb: borderArgb } };
  const metaBorder = { top: edge, left: edge, bottom: edge, right: edge } as ExcelJS.Borders;
  for (let c = 1; c <= lastCol; c++) {
    const cell = ws.getCell(r0, c);
    cell.font = { bold: true };
    cell.fill = sectionTitleFill;
    cell.alignment = { vertical: "middle", horizontal: "left" };
  }
  const master = ws.getCell(r0, 1);
  master.border = metaBorder;
  master.alignment = { vertical: "middle", horizontal: "left", wrapText: true };
  // 結合行の右端枠は最終列セル側に付けないと欠ける/色が出ないことがある
  ws.getCell(r0, lastCol).border = metaBorder;
  // 結合セルの右端枠は最終列セルに付けないと欠けることがあるため、行外周を明示的に付与
  applyOutlineBorder(ws, r0, 1, r0, lastCol, borderArgb);
  onMergedRow?.(r0, borderArgb);
}

function appendCustomerDataRows(
  ws: ExcelJS.Worksheet,
  block: CustomerShipBlock,
  activeDays: number,
  lastCol: number,
  theme: SectionTheme,
) {
  for (const r of resolveCustomerRows(block, activeDays)) {
    const prevCell = r.prev != null ? excelQty(r.prev) : "";
    ws.addRow(
      padRow(
        [r.spec.label, excelQty(r.rowSum), prevCell, ...dayValues31Active(r.series, activeDays)],
        lastCol,
      ),
    );
    ws.getCell(ws.rowCount, 1).fill = theme.veryLightFill;
  }
}

function appendSupplierDataRows(ws: ExcelJS.Worksheet, block: SupplierBlock, activeDays: number, lastCol: number) {
  const supplierTheme = sectionTheme(gonenSupplierBlockKaisoIndex(block));
  for (const r of resolveSupplierRows(block, activeDays)) {
    const prevCell = r.prev != null ? excelQty(r.prev) : "";
    ws.addRow(
      padRow(
        [r.spec.label, excelQty(r.rowSum), prevCell, ...dayValues31Active(r.series, activeDays)],
        lastCol,
      ),
    );
    ws.getCell(ws.rowCount, 1).fill = supplierTheme.veryLightFill;
  }
}

export type GonenMultiMonthExcelSlice = {
  yearMonth: string;
  oracle: GonenKukumiOracleSuccess;
};

type SectionRange = {
  top: number;
  bottom: number;
  theme: SectionTheme;
  titleRow: number;
  headerRow: number;
};

function sortExcelMonths(slices: GonenMultiMonthExcelSlice[]): GonenMultiMonthExcelSlice[] {
  return [...slices].sort((a, b) =>
    compareGonenKukumiYearMonth(normalizeYearMonth(a.yearMonth), normalizeYearMonth(b.yearMonth)),
  );
}

/** Web の複数月ビューと同じ階層（セクション＝ブロック、その下に各月の「検索年月」→表）。日次 31 列・パッド日グレーも同様。 */
export async function buildGonenKukumiExcelBufferForMonths(
  months: GonenMultiMonthExcelSlice[],
  baseParams: GonenExcelExportParams,
): Promise<ArrayBuffer> {
  const sorted = sortExcelMonths(months);
  if (sorted.length === 0) {
    throw new Error("Excel: 出力する月がありません");
  }

  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet("5年9組", {
    properties: { defaultRowHeight: 18 },
  });

  const lastCol = lastColIndexFixed();
  const headCells = ["区分", "行計", "前月残／在庫", ...dayHeaders(GONEN_REPORT_GRID_DAYS)];
  const baseYm = normalizeYearMonth(baseParams.yearMonth);

  const cache: Record<string, GonenKukumiOracleSuccess> = {};
  for (const s of sorted) {
    cache[normalizeYearMonth(s.yearMonth)] = s.oracle;
  }

  const sortedYmList = sorted.map((s) => normalizeYearMonth(s.yearMonth));
  /** groupSegmentsFromCache は基準月の Oracle が必要。無い場合は先頭の表示月で並べる */
  const baseYmForGrouping = cache[baseYm] ? baseYm : sortedYmList[0]!;
  const bannerOracle = cache[baseYm] ?? cache[baseYmForGrouping] ?? sorted[0]!.oracle;
  let segments = groupSegmentsFromCache(cache, baseYmForGrouping);
  if (segments.length === 0 && sortedYmList.length > 0) {
    segments = groupSegmentsFromCache(cache, sortedYmList[0]!);
  }

  ws.mergeCells(1, 1, 1, lastCol);
  const title = ws.getCell(1, 1);
  title.value = "5年9組";
  title.font = { bold: true, size: 14 };
  title.alignment = { vertical: "middle" };

  const condHeaderRow = ws.rowCount + 1;
  ws.addRow(padRow(["得意先コード", "得意先品目", "品目任意変換値"], lastCol));
  ws.addRow(padRow([baseParams.custCode, baseParams.custItem, baseParams.optionChange], lastCol));
  ws.addRow(padRow(["検索年月（基準）", "対象日付", "内作品番"], lastCol));
  ws.addRow(padRow([baseYm, baseParams.asOfDate, bannerOracle.internalItemCd], lastCol));
  const condEndRow = ws.rowCount;
  styleCondKeyRow(ws, condHeaderRow, lastCol);
  styleCondKeyRow(ws, condHeaderRow + 2, lastCol);

  const sectionRanges: SectionRange[] = [];
  const mergedRowBorders: Array<{ row: number; borderArgb: string }> = [];
  let thousandAnchorRow: number | null = null;
  const markThousandAnchor = () => {
    if (thousandAnchorRow == null) thousandAnchorRow = ws.rowCount;
  };
  const markMergedRow = (row: number, borderArgb: string) => {
    mergedRowBorders.push({ row, borderArgb });
  };
  const appendMeta = (text: string, fill: ExcelJS.Fill, borderArgb?: string) =>
    appendMergedMetaRow(ws, text, lastCol, fill, borderArgb ?? GONEN_FIXED_GRID_BORDER_EXCEL_ARGB, markMergedRow);

  const fillAmberNote: ExcelJS.Fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: "FFFFEDD5" },
  };
  const fillSlateNote: ExcelJS.Fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: "FFF8FAFC" },
  };

  for (const segment of segments) {
    const segTheme = sectionTheme(gonenSegmentKaisoIndex(segment, bannerOracle));

    if (segment.kind === "cust" && segment.filter) {
      const b = findCustomerBlock(bannerOracle.customerBlocks, segment.filter);
      if (b) {
        appendMeta(customerBannerLine(b), segTheme.baseFill, segTheme.titleBorderArgb);
      } else {
        appendMeta("基準月に該当の得意先行がありません", segTheme.baseFill, segTheme.titleBorderArgb);
      }
    } else if (segment.kind === "sup" && segment.filter) {
      const block = findSupplierBlock(bannerOracle.supplierBlocks, segment.filter);
      if (block) {
        appendMeta(supplierBannerLine(block), segTheme.baseFill, segTheme.titleBorderArgb);
      } else {
        appendMeta("基準月に該当の仕入先行がありません", segTheme.baseFill, segTheme.titleBorderArgb);
      }
    }

    for (const ym of sortedYmList) {
      const oracle = cache[ym];
      const ymLine = `検索年月 ${ym}${ym === baseYm ? "（基準）" : ""}`;
      appendMeta(ymLine, segTheme.baseFill, segTheme.titleBorderArgb);
      const titleRow = ws.rowCount;

      if (!oracle) {
        appendMeta(`${ym} のデータを読み込めませんでした。`, fillAmberNote);
        continue;
      }

      if (segment.kind === "cust" && segment.filter) {
        const block = findCustomerBlock(oracle.customerBlocks, segment.filter);
        if (!block) {
          appendMeta("この月は該当の得意先行がありません。", fillSlateNote);
          continue;
        }
        const theme = sectionTheme(gonenSegmentKaisoIndex(segment, oracle));
        markThousandAnchor();

        const activeDays = daysInMonthYm(ym);
        const holidaySet = new Set(oracle.holidayDays);

        ws.addRow(padRow(headCells, lastCol));
        const headerRow = ws.rowCount;
        styleSupplierKaisoHeaderRow(ws, headerRow, lastCol, activeDays, theme.baseFill);

        const dataStart = ws.rowCount + 1;
        appendCustomerDataRows(ws, block, activeDays, lastCol, theme);
        const dataEnd = ws.rowCount;

        applyDayColumnFillsToRange(ws, dataStart, dataEnd, activeDays, holidaySet, theme.baseFill);
        applyPadDayColumnFills(ws, dataStart, dataEnd, activeDays);

        sectionRanges.push({ top: titleRow, bottom: ws.rowCount, theme, titleRow, headerRow });
      } else if (segment.kind === "sup" && segment.filter) {
        const block = findSupplierBlock(oracle.supplierBlocks, segment.filter);
        if (!block) {
          appendMeta("この月は該当の仕入先行がありません。", fillSlateNote);
          continue;
        }
        const theme = sectionTheme(gonenSupplierBlockKaisoIndex(block));
        markThousandAnchor();

        const activeDays = daysInMonthYm(ym);
        const holidaySet = new Set(oracle.holidayDays);

        ws.addRow(padRow(headCells, lastCol));
        const headerRow = ws.rowCount;
        styleSupplierKaisoHeaderRow(ws, headerRow, lastCol, activeDays, theme.baseFill);

        const dataStart = ws.rowCount + 1;
        appendSupplierDataRows(ws, block, activeDays, lastCol);
        const dataEnd = ws.rowCount;
        applyDayColumnFillsToRange(ws, dataStart, dataEnd, activeDays, holidaySet, theme.baseFill);
        applyPadDayColumnFills(ws, dataStart, dataEnd, activeDays);

        sectionRanges.push({ top: titleRow, bottom: ws.rowCount, theme, titleRow, headerRow });
      }
    }
  }

  applyThinBordersMergeAware(ws, 1, ws.rowCount, lastCol, GONEN_FIXED_GRID_BORDER_EXCEL_ARGB);
  clearCondBlockDayColumnFills(ws, condHeaderRow, condEndRow, lastCol);

  // 結合帯（得意先/仕入先帯・検索年月帯）は、全体枠（灰色）で上書きされるため階層色で付け直す
  for (const m of mergedRowBorders) {
    const edge = { style: "thin" as const, color: { argb: m.borderArgb } };
    const full = { top: edge, left: edge, bottom: edge, right: edge } as ExcelJS.Borders;
    ws.getCell(m.row, 1).master.border = full;
    ws.getCell(m.row, lastCol).border = full;
    applyOutlineBorder(ws, m.row, 1, m.row, lastCol, m.borderArgb);
  }

  for (const s of sectionRanges) {
    applyOutlineBorder(ws, s.top, 1, s.bottom, lastCol, s.theme.outerBorderArgb);
    applyFullBorderToRowMergeAware(ws, s.titleRow, lastCol, s.theme.titleBorderArgb);
    applyFullBorderToRowMergeAware(ws, s.headerRow, lastCol, s.theme.titleBorderArgb);
    applyOutlineBorder(ws, s.headerRow, 1, s.bottom, lastCol, s.theme.outerBorderArgb);
  }

  const anchor = thousandAnchorRow ?? condEndRow;
  applyThousandSeparatorToTableNumbers(ws, anchor, ws.rowCount, lastCol);

  ws.columns = Array.from({ length: lastCol }, (_, i) => ({
    width: i < 3 ? (i === 0 ? 14 : 10) : 6,
  }));

  const firstScrollRow = condEndRow + 1;
  ws.views = [
    {
      state: "frozen",
      ySplit: condEndRow,
      topLeftCell: `A${firstScrollRow}`,
      activeCell: `A${firstScrollRow}`,
    },
  ];

  applyMsGothicToUsedRange(ws, lastCol, ws.rowCount);

  const buf = await wb.xlsx.writeBuffer();
  return buf as ArrayBuffer;
}

/** 1 シート・日次 31 列固定（未使用日はグレー） */
export async function buildGonenKukumiExcelBuffer(
  oracle: GonenKukumiOracleSuccess,
  params: GonenExcelExportParams,
): Promise<ArrayBuffer> {
  return buildGonenKukumiExcelBufferForMonths([{ yearMonth: params.yearMonth, oracle }], params);
}

/** Windows 等でファイル名に使えない文字を置換 */
function sanitizeExcelFilenameSegment(s: string): string {
  const t = s.replace(/[/\\:*?"<>|]/g, "_").trim();
  return t.length > 0 ? t : "_";
}

/** 東京日時を yyyyMMddHHmmss で返す（出力ボタン押下時刻） */
function formatExportedAtYmdHmsTokyo(exportedAt: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(exportedAt);
  const get = (type: Intl.DateTimeFormatPart["type"]) =>
    (parts.find((p) => p.type === type)?.value ?? "").replace(/\D/g, "");
  const y = get("year");
  const mo = get("month").padStart(2, "0");
  const d = get("day").padStart(2, "0");
  const h = get("hour").padStart(2, "0");
  const min = get("minute").padStart(2, "0");
  const sec = get("second").padStart(2, "0");
  return `${y}${mo}${d}${h}${min}${sec}`;
}

/** 得意先コード_得意先品目_検索年月(スラッシュなし)_yyyyMMddHHmmss（東京）.xlsx */
export function defaultGonenExcelFilename(
  params: GonenExcelExportParams,
  exportedAt: Date = new Date(),
): string {
  const ym = params.yearMonth.replace(/\//g, "");
  const ts = formatExportedAtYmdHmsTokyo(exportedAt);
  const code = sanitizeExcelFilenameSegment(params.custCode);
  const item = sanitizeExcelFilenameSegment(params.custItem);
  return `${code}_${item}_${ym}_${ts}.xlsx`;
}

/** 複数月: 得意先コード_得意先品目_最初の月_最後の月_yyyyMMddHHmmss（東京）.xlsx */
export function defaultGonenMultiMonthExcelFilename(
  baseParams: GonenExcelExportParams,
  yearMonths: string[],
  exportedAt: Date = new Date(),
): string {
  const sorted = [...yearMonths].map(normalizeYearMonth).sort(compareGonenKukumiYearMonth);
  const ym0 = (sorted[0] ?? baseParams.yearMonth).replace(/\//g, "");
  const ym1 = (sorted[sorted.length - 1] ?? baseParams.yearMonth).replace(/\//g, "");
  const ts = formatExportedAtYmdHmsTokyo(exportedAt);
  const code = sanitizeExcelFilenameSegment(baseParams.custCode);
  const item = sanitizeExcelFilenameSegment(baseParams.custItem);
  const range = ym0 === ym1 ? ym0 : `${ym0}-${ym1}`;
  return `${code}_${item}_${range}_${ts}.xlsx`;
}
