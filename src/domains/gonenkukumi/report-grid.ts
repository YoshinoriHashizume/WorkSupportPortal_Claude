import type { DayQtySeries } from "@/domains/gonenkukumi/types";

/** 日次列は常に 31 列（月に無い日はパディング列で埋める）。Web / Excel で共通 */
export const GONEN_REPORT_GRID_DAYS = 31;

/** 未使用日列の塗り（Web / Excel で同系色に揃える） */
export const GONEN_PAD_DAY_HEX = "#b8c4d0";

/** `GONEN_PAD_DAY_HEX` に対応する Excel ARGB */
export const GONEN_PAD_DAY_EXCEL_ARGB = "FFB8C4D0";

export const GONEN_FIXED_GRID_BORDER_HEX = "#E2E8F0";

export const GONEN_FIXED_GRID_BORDER_EXCEL_ARGB = "FFE2E8F0";

/**
 * 日次列（31 列）の空配列を新規生成して返す。
 * 共有参照すると累積処理（`addToDay` 等）で他のブロックの値を破壊するため、
 * 必ず毎回新しい配列を返す。
 */
export function createEmptyDayQtySeries(
  maxDays: number = GONEN_REPORT_GRID_DAYS,
): DayQtySeries {
  return Array.from({ length: maxDays }, () => null);
}

const YEAR_MONTH_RE = /^(\d{4})\/(\d{1,2})$/;

/** 検索年月 yyyy/mm からその月の「有効」日数（2月=28/29 等） */
export function daysInMonthYm(ym: string): number {
  const m = YEAR_MONTH_RE.exec(ym.trim());
  if (!m) return GONEN_REPORT_GRID_DAYS;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  if (mo < 1 || mo > 12) return GONEN_REPORT_GRID_DAYS;
  return new Date(y, mo, 0).getDate();
}

export function ymdForDay(ym: string, day: number): Date | null {
  const m = YEAR_MONTH_RE.exec(ym.trim());
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  if (mo < 1 || mo > 12 || day < 1 || day > 31) return null;
  return new Date(y, mo - 1, day);
}

/** 月の 1〜activeDays 日のみ合計（行計用）。日次列は最大 `maxDays`（既定 31） */
export function sumDayQtySeriesActiveDays(
  series: DayQtySeries,
  activeDays: number,
  maxDays: number = GONEN_REPORT_GRID_DAYS,
): number | null {
  let t = 0;
  let any = false;
  const n = Math.min(activeDays, series.length, maxDays);
  for (let i = 0; i < n; i++) {
    const v = series[i];
    if (v != null && v !== 0) {
      t += v;
      any = true;
    }
  }
  return any ? t : null;
}

/** API 経由で数値が文字列化した場合も日次セルに出す（月初発注ワーク用） */
export function normalizeDayQtySeries31(
  series: DayQtySeries | undefined | null,
  maxDays: number = GONEN_REPORT_GRID_DAYS,
): DayQtySeries {
  const out = createEmptyDayQtySeries(maxDays);
  if (!series || !Array.isArray(series)) return out;
  for (let i = 0; i < maxDays; i++) {
    const v = series[i] as unknown;
    if (v === null || v === undefined) continue;
    if (typeof v === "number") {
      out[i] = Number.isFinite(v) ? v : null;
      continue;
    }
    if (typeof v === "string") {
      const n = Number(v.replace(/,/g, "").replace(/\s/g, "").trim());
      out[i] = Number.isFinite(n) ? n : null;
    }
  }
  return out;
}
