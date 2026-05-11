import type {
  CustomerShipBlock,
  CustomerTotalsBlock,
  DayQtySeries,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";
import {
  GONEN_REPORT_GRID_DAYS,
  normalizeDayQtySeries31,
  sumDayQtySeriesActiveDays,
} from "@/domains/gonenkukumi/report-grid";

const EMPTY_DAY_SERIES: DayQtySeries = Array.from(
  { length: GONEN_REPORT_GRID_DAYS },
  () => null,
);

function emptySeries(): DayQtySeries {
  return EMPTY_DAY_SERIES;
}

/**
 * 行計の値（共通仕様）。
 * - `useZaiko` のとき: 在庫値をそのまま返す（null の場合もそのまま）
 * - それ以外: 日別合計 + 前月残。両方が無ければ null。
 */
export function gonenRowSum(args: {
  daysSum: number | null;
  prevAdd: number;
  zaiko: number | null;
  useZaiko: boolean;
}): number | null {
  if (args.useZaiko) return args.zaiko;
  if (args.daysSum == null && args.prevAdd === 0) return null;
  return (args.daysSum ?? 0) + args.prevAdd;
}

/* ============================== Customer ============================== */

export type CustomerRowSpec = {
  label: "内示受注" | "確定受注" | "統合受注" | "出荷実績" | "売上実績" | "本日在庫";
  series: (b: CustomerShipBlock) => DayQtySeries;
  /** 前月残列に表示する値。null の場合は空欄。 */
  prev: (b: CustomerShipBlock) => number | null;
  rowSumKind: "sum" | "zaiko";
  /** Web 用の Tailwind テキスト色クラス */
  webClass: string;
};

export const CUSTOMER_ROW_SPECS: readonly CustomerRowSpec[] = [
  {
    label: "内示受注",
    series: (b) => b.uncnfmByDay,
    prev: () => null,
    rowSumKind: "sum",
    webClass: "text-violet-700",
  },
  {
    label: "確定受注",
    series: (b) => b.confirmedOrderByDay,
    prev: (b) => b.confirmedOrderPrevBalance,
    rowSumKind: "sum",
    webClass: "text-blue-700",
  },
  {
    label: "統合受注",
    series: (b) => b.uniteOrderByDay,
    prev: () => null,
    rowSumKind: "sum",
    webClass: "text-red-600",
  },
  {
    label: "出荷実績",
    series: (b) => b.shipByDay,
    prev: () => null,
    rowSumKind: "sum",
    webClass: "text-slate-900",
  },
  {
    label: "売上実績",
    series: (b) => b.salesByDay,
    prev: () => null,
    rowSumKind: "sum",
    webClass: "text-pink-600",
  },
  {
    label: "本日在庫",
    series: () => emptySeries(),
    prev: () => null,
    rowSumKind: "zaiko",
    webClass: "text-amber-900",
  },
];

export type ResolvedCustomerRow = {
  spec: CustomerRowSpec;
  series: DayQtySeries;
  prev: number | null;
  rowSum: number | null;
};

export function resolveCustomerRows(
  block: CustomerShipBlock,
  activeDays: number,
): ResolvedCustomerRow[] {
  return CUSTOMER_ROW_SPECS.map((spec) => {
    const series = spec.series(block);
    const useZaiko = spec.rowSumKind === "zaiko";
    const prev = spec.prev(block);
    const daysSum = useZaiko ? null : sumDayQtySeriesActiveDays(series, activeDays);
    const rowSum = gonenRowSum({
      daysSum,
      prevAdd: prev ?? 0,
      zaiko: block.zaiko,
      useZaiko,
    });
    return { spec, series, prev, rowSum };
  });
}

/* ============================== Supplier ============================== */

export type SupplierRowSpec = {
  label: "月初発注" | "所要量" | "確定発注" | "入荷実績" | "本日在庫";
  series: (b: SupplierBlock) => DayQtySeries;
  /** 前月残列の値を block から決定する。null 返却は空欄。 */
  prev: (b: SupplierBlock) => number | null;
  rowSumKind: "sum" | "zaiko";
  webClass: string;
};

export const SUPPLIER_ROW_SPECS: readonly SupplierRowSpec[] = [
  {
    label: "月初発注",
    series: (b) => normalizeDayQtySeries31(b.monthlyStartByDay),
    prev: () => null,
    rowSumKind: "sum",
    webClass: "text-violet-700",
  },
  {
    label: "所要量",
    series: (b) => b.demandByDay,
    prev: () => null,
    rowSumKind: "sum",
    webClass: "text-emerald-700",
  },
  {
    label: "確定発注",
    series: (b) => b.confirmedPuchByDay,
    prev: (b) => b.confirmedPuchPrevBalance,
    rowSumKind: "sum",
    webClass: "text-blue-700",
  },
  {
    label: "入荷実績",
    series: (b) => b.receiptByDay,
    prev: () => null,
    rowSumKind: "sum",
    webClass: "text-slate-900",
  },
  {
    label: "本日在庫",
    series: () => emptySeries(),
    prev: () => null,
    rowSumKind: "zaiko",
    webClass: "text-amber-900",
  },
];

export type ResolvedSupplierRow = {
  spec: SupplierRowSpec;
  series: DayQtySeries;
  prev: number | null;
  rowSum: number | null;
};

export function resolveSupplierRows(
  block: SupplierBlock,
  activeDays: number,
): ResolvedSupplierRow[] {
  return SUPPLIER_ROW_SPECS.map((spec) => {
    const series = spec.series(block);
    const useZaiko = spec.rowSumKind === "zaiko";
    const prev = spec.prev(block);
    const daysSum = useZaiko ? null : sumDayQtySeriesActiveDays(series, activeDays);
    const rowSum = gonenRowSum({
      daysSum,
      prevAdd: prev ?? 0,
      zaiko: block.zaiko,
      useZaiko,
    });
    return { spec, series, prev, rowSum };
  });
}

/* =============================== Totals =============================== */

export type CustomerTotalsRowSpec = {
  label: "内示受注 計" | "確定受注 計" | "統合受注 計" | "出荷実績 計" | "売上実績 計";
  series: (t: CustomerTotalsBlock) => DayQtySeries;
};

export const CUSTOMER_TOTALS_ROW_SPECS: readonly CustomerTotalsRowSpec[] = [
  { label: "内示受注 計", series: (t) => t.uncnfmByDay },
  { label: "確定受注 計", series: (t) => t.confirmedOrderByDay },
  { label: "統合受注 計", series: (t) => t.uniteOrderByDay },
  { label: "出荷実績 計", series: (t) => t.shipByDay },
  { label: "売上実績 計", series: (t) => t.salesByDay },
];

export type ResolvedTotalsRow = {
  spec: CustomerTotalsRowSpec;
  series: DayQtySeries;
  rowSum: number | null;
};

export function resolveCustomerTotalsRows(
  totals: CustomerTotalsBlock,
  activeDays: number,
): ResolvedTotalsRow[] {
  return CUSTOMER_TOTALS_ROW_SPECS.map((spec) => {
    const series = spec.series(totals);
    const rowSum = sumDayQtySeriesActiveDays(series, activeDays);
    return { spec, series, rowSum };
  });
}
