/** 検索年月の前月／次月ナビ（検索画面と同じ上下限: MIN 2022/01、上限は対象日付の6か月後の暦月） */

import type { GonenKukumiSearchInput } from "@/domains/gonenkukumi/schemas";

export const GONENKUKUMI_MIN_SEARCH_YM = "2022/01";

/** 今日の yyyy/mm */
export function todayYm(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}/${m}`;
}

/** 今日の yyyy/mm/dd */
export function todayYmd(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}/${m}/${day}`;
}

/** yyyy/mm を符号付きで比較（昇順 < / 同値 0 / 降順 >）。parse 失敗時は 0 を返す */
export function compareYm(a: string, b: string): number {
  const ma = /^(\d{4})\/(\d{2})$/.exec(a.trim());
  const mb = /^(\d{4})\/(\d{2})$/.exec(b.trim());
  if (!ma || !mb) return 0;
  const ya = Number(ma[1]);
  const moa = Number(ma[2]);
  const yb = Number(mb[1]);
  const mob = Number(mb[2]);
  if (ya !== yb) return ya - yb;
  return moa - mob;
}

/** 対象日付の 6 か月後の暦月（yyyy/mm）。検索可能上限の計算用 */
export function maxYmFromAsOf(asOfSlash: string): string {
  const m = /^(\d{4})\/(\d{2})\/(\d{2})$/.exec(asOfSlash.trim());
  if (!m) return todayYm();
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  d.setMonth(d.getMonth() + 6);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}/${mo}`;
}

/** 対象日付に対する検索年月の選択可能範囲（min: 固定 2022/01、max: 対象日付+6 か月の暦月） */
export function yearMonthBounds(asOfSlash: string): { min: string; max: string } {
  const cap = maxYmFromAsOf(asOfSlash);
  if (compareYm(cap, GONENKUKUMI_MIN_SEARCH_YM) < 0) {
    return { min: GONENKUKUMI_MIN_SEARCH_YM, max: GONENKUKUMI_MIN_SEARCH_YM };
  }
  return { min: GONENKUKUMI_MIN_SEARCH_YM, max: cap };
}

/** ym を min..max の範囲に収める（範囲外は端へクランプ） */
export function clampYm(ym: string, minYm: string, maxYm: string): string {
  if (compareYm(ym, minYm) < 0) return minYm;
  if (compareYm(ym, maxYm) > 0) return maxYm;
  return ym;
}

/** min..max の範囲を 1 か月刻みで列挙（昇順、両端含む）。max < min のときは [min] を返す */
export function ymOptionsList(minYm: string, maxYm: string): string[] {
  if (compareYm(maxYm, minYm) < 0) return [minYm];
  const out: string[] = [];
  const [sy, sm] = minYm.split("/").map(Number);
  const [ey, em] = maxYm.split("/").map(Number);
  let y = sy!;
  let mo = sm!;
  while (y < ey! || (y === ey! && mo <= em!)) {
    out.push(`${y}/${String(mo).padStart(2, "0")}`);
    mo++;
    if (mo > 12) {
      mo = 1;
      y++;
    }
  }
  return out;
}

/** 表示用ラベル「2024年04月」形式（year-month-nav と検索画面で共通） */
export function formatYmJaLabel(ym: string): string {
  const m = /^(\d{4})\/(\d{2})$/.exec(ym.trim());
  if (!m) return ym;
  return `${m[1]}年${m[2]}月`;
}

/** yyyy/mm/dd → yyyy-MM-dd（HTML `<input type="date">` 用） */
export function ymdSlashToIso(ymd: string): string {
  const m = /^(\d{4})\/(\d{2})\/(\d{2})$/.exec(ymd.trim());
  if (!m) return "";
  return `${m[1]}-${m[2]}-${m[3]}`;
}

/** yyyy-MM-dd → yyyy/mm/dd（API・スキーマ用） */
export function isoToYmdSlash(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!m) return iso.trim();
  return `${m[1]}/${m[2]}/${m[3]}`;
}

export function normalizeYearMonth(ym: string): string {
  const m = /^(\d{4})\/(\d{1,2})$/.exec(ym.trim());
  if (!m) return ym.trim();
  return `${m[1]}/${String(Number(m[2])).padStart(2, "0")}`;
}

/** 検索年月 yyyy/mm の昇順ソート用（同一値は 0） */
export function compareGonenKukumiYearMonth(a: string, b: string): number {
  return compareYm(normalizeYearMonth(a), normalizeYearMonth(b));
}

/** 暦月を delta 分だけずらす（yyyy/mm） */
export function addMonthsYm(ym: string, delta: number): string {
  const m = /^(\d{4})\/(\d{2})$/.exec(normalizeYearMonth(ym));
  if (!m) return ym.trim();
  let y = Number(m[1]);
  let mo = Number(m[2]) + delta;
  while (mo < 1) {
    mo += 12;
    y -= 1;
  }
  while (mo > 12) {
    mo -= 12;
    y += 1;
  }
  return `${y}/${String(mo).padStart(2, "0")}`;
}

function ymInBounds(ym: string, min: string, max: string): boolean {
  return compareYm(ym, min) >= 0 && compareYm(ym, max) <= 0;
}

/**
 * 結果ページのナビゲーション／URL ビルド用パラメータ。
 * 検索フォームのスキーマと一致するため `GonenKukumiSearchInput` を別名で公開する。
 */
export type GonenResultNavParams = GonenKukumiSearchInput;

/** 前月・次月に移れるときだけ yyyy/mm を返す（範囲外は null） */
export function getPrevNextYearMonth(
  yearMonth: string,
  asOfDate: string,
): { prev: string | null; next: string | null } {
  const { min, max } = yearMonthBounds(asOfDate);
  const cur = normalizeYearMonth(yearMonth);
  const prevCandidate = addMonthsYm(cur, -1);
  const nextCandidate = addMonthsYm(cur, 1);
  const prev = ymInBounds(prevCandidate, min, max) ? prevCandidate : null;
  const next = ymInBounds(nextCandidate, min, max) ? nextCandidate : null;
  return { prev, next };
}

export function buildGonenKukumiResultUrl(p: GonenResultNavParams): string {
  const q = new URLSearchParams({
    custCode: p.custCode,
    custItem: p.custItem,
    optionChange: (p.optionChange?.trim() ? p.optionChange : "*") || "*",
    yearMonth: normalizeYearMonth(p.yearMonth),
    asOfDate: p.asOfDate,
  });
  return `/app/production/five-year-nine/result?${q}`;
}
