/** 検索年月の前月／次月ナビ（検索画面と同じ上下限: MIN 2022/01、上限は対象日付の6か月後の暦月） */

export const GONENKUKUMI_MIN_SEARCH_YM = "2022/01";

function todayYm(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}/${m}`;
}

function compareYm(a: string, b: string): number {
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

function maxYmFromAsOf(asOfSlash: string): string {
  const m = /^(\d{4})\/(\d{2})\/(\d{2})$/.exec(asOfSlash.trim());
  if (!m) return todayYm();
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  d.setMonth(d.getMonth() + 6);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}/${mo}`;
}

function yearMonthBounds(asOfSlash: string): { min: string; max: string } {
  const cap = maxYmFromAsOf(asOfSlash);
  if (compareYm(cap, GONENKUKUMI_MIN_SEARCH_YM) < 0) {
    return { min: GONENKUKUMI_MIN_SEARCH_YM, max: GONENKUKUMI_MIN_SEARCH_YM };
  }
  return { min: GONENKUKUMI_MIN_SEARCH_YM, max: cap };
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

export type GonenResultNavParams = {
  custCode: string;
  custItem: string;
  optionChange: string;
  yearMonth: string;
  asOfDate: string;
};

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
