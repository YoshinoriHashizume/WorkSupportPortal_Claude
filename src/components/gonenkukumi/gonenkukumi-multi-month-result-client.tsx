"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { custHeadlineFromOracle } from "@/domains/gonenkukumi/cust-headline";
import type { GonenKukumiOracleSuccess } from "@/domains/gonenkukumi/types";
import {
  compareGonenKukumiYearMonth,
  getPrevNextYearMonth,
  normalizeYearMonth,
} from "@/domains/gonenkukumi/year-month-nav";
import { kaisoColor } from "@/domains/gonenkukumi/kaiso-color";
import { GonenKukumiExcelExportButton } from "@/components/gonenkukumi/gonenkukumi-excel-export-button";
import {
  GonenKukumiOracleMonthPanels,
  type GonenKukumiResultPanelParams,
} from "@/components/gonenkukumi/gonenkukumi-oracle-month-panels";
import {
  groupSegmentsFromCache,
  panelSegmentKey,
  type GonenPanelSegment,
} from "@/domains/gonenkukumi/panel-segments";
import {
  findCustomerBlock,
  findSupplierBlock,
} from "@/domains/gonenkukumi/block-finders";
import { gonenSegmentKaisoIndex } from "@/domains/gonenkukumi/segment-theme";
import {
  CustomerBannerHeader,
  SupplierBannerHeader,
} from "@/components/gonenkukumi/block-banner-header";

function monthsHaveYm(months: string[], ym: string): boolean {
  const n = normalizeYearMonth(ym);
  return months.some((m) => normalizeYearMonth(m) === n);
}

function addMonthToSorted(months: string[], ym: string): string[] {
  const n = normalizeYearMonth(ym);
  const set = new Set(months.map(normalizeYearMonth));
  set.add(n);
  return [...set].sort(compareGonenKukumiYearMonth);
}

function segmentSectionTheme(seg: GonenPanelSegment, banner: GonenKukumiOracleSuccess) {
  return kaisoColor(gonenSegmentKaisoIndex(seg, banner));
}

export function GonenKukumiMultiMonthResultClient({
  initialOracle,
  initialParams,
}: {
  initialOracle: GonenKukumiOracleSuccess;
  initialParams: GonenKukumiResultPanelParams;
}) {
  const baseYm = normalizeYearMonth(initialParams.yearMonth);
  const [oracleCache, setOracleCache] = useState<Record<string, GonenKukumiOracleSuccess>>(() => ({
    [baseYm]: initialOracle,
  }));
  const cacheRef = useRef(oracleCache);
  cacheRef.current = oracleCache;

  const [loadedMonths, setLoadedMonths] = useState<string[]>(() => [baseYm]);

  const [openMap, setOpenMap] = useState<Record<string, boolean>>(() => {
    const o: Record<string, boolean> = {};
    for (const seg of groupSegmentsFromCache({ [baseYm]: initialOracle }, baseYm)) {
      o[`${panelSegmentKey(seg)}:${baseYm}`] = true;
    }
    return o;
  });

  const [busy, setBusy] = useState(false);

  const panelSegments = useMemo(
    () => groupSegmentsFromCache(oracleCache, baseYm),
    [oracleCache, baseYm],
  );

  /** セクション見出し帯は URL 基準月の代表行で固定（月を追加してもブロック単位のタイトル位置は変えない） */
  const bannerOracle = useMemo(
    () => oracleCache[baseYm] ?? initialOracle,
    [oracleCache, baseYm, initialOracle],
  );

  const sortedLoadedMonths = useMemo(
    () => [...loadedMonths].map(normalizeYearMonth).sort(compareGonenKukumiYearMonth),
    [loadedMonths],
  );

  const minYm = sortedLoadedMonths[0];
  const maxYm = sortedLoadedMonths[sortedLoadedMonths.length - 1];
  const prevEdge = minYm ? getPrevNextYearMonth(minYm, initialParams.asOfDate).prev : null;
  const nextEdge = maxYm ? getPrevNextYearMonth(maxYm, initialParams.asOfDate).next : null;
  const prevDisabled = !prevEdge || monthsHaveYm(loadedMonths, prevEdge) || busy;
  const nextDisabled = !nextEdge || monthsHaveYm(loadedMonths, nextEdge) || busy;

  const appendMonthAll = useCallback(
    async (dir: "prev" | "next") => {
      if (!sortedLoadedMonths.length || busy) return;
      const min = sortedLoadedMonths[0]!;
      const max = sortedLoadedMonths[sortedLoadedMonths.length - 1]!;
      const targetRaw =
        dir === "prev"
          ? getPrevNextYearMonth(min, initialParams.asOfDate).prev
          : getPrevNextYearMonth(max, initialParams.asOfDate).next;
      if (!targetRaw) return;
      const targetYm = normalizeYearMonth(targetRaw);
      if (monthsHaveYm(loadedMonths, targetYm)) return;

      setBusy(true);
      try {
        let oracle: GonenKukumiOracleSuccess | undefined = cacheRef.current[targetYm];
        if (!oracle) {
          const res = await fetch("/api/gonenkukumi/oracle-result", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              custCode: initialParams.custCode,
              custItem: initialParams.custItem,
              optionChange: initialParams.optionChange,
              yearMonth: targetYm,
              asOfDate: initialParams.asOfDate,
            }),
          });
          const data: unknown = await res.json().catch(() => ({}));
          if (!res.ok) {
            const msg =
              typeof data === "object" && data && "error" in data && typeof (data as { error: unknown }).error === "string"
                ? (data as { error: string }).error
                : "データの取得に失敗しました。";
            window.alert(msg);
            return;
          }
          if (
            typeof data !== "object" ||
            !data ||
            !("oracle" in data) ||
            typeof (data as { oracle: unknown }).oracle !== "object" ||
            !(data as { oracle: { ok?: boolean } }).oracle ||
            (data as { oracle: { ok?: boolean } }).oracle.ok !== true
          ) {
            window.alert("データの形式が不正です。");
            return;
          }
          oracle = (data as { oracle: GonenKukumiOracleSuccess }).oracle;
          setOracleCache((c) => (c[targetYm] ? c : { ...c, [targetYm]: oracle! }));
        }

        const mergedCache: Record<string, GonenKukumiOracleSuccess> = {
          ...cacheRef.current,
          [targetYm]: oracle!,
        };
        const segs = groupSegmentsFromCache(mergedCache, baseYm);

        setLoadedMonths((m) => addMonthToSorted(m, targetYm));
        setOpenMap((prev) => {
          const next = { ...prev };
          for (const seg of segs) {
            next[`${panelSegmentKey(seg)}:${targetYm}`] = true;
          }
          return next;
        });
      } catch {
        window.alert("データの取得に失敗しました。");
      } finally {
        setBusy(false);
      }
    },
    [baseYm, busy, initialParams, loadedMonths, sortedLoadedMonths],
  );

  const custDisplay = custHeadlineFromOracle(initialParams.custCode, initialOracle);

  const excelMultiMonthSlices = useMemo(
    () =>
      sortedLoadedMonths
        .map((ym) => {
          const n = normalizeYearMonth(ym);
          const o = oracleCache[n];
          return o ? { yearMonth: n, oracle: o } : null;
        })
        .filter((x): x is { yearMonth: string; oracle: GonenKukumiOracleSuccess } => x != null),
    [oracleCache, sortedLoadedMonths],
  );

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
          <h2 className="text-sm font-semibold text-slate-800">検索条件</h2>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={prevDisabled}
                title={
                  prevEdge
                    ? `全ブロックに ${prevEdge} を追加（得意先・全仕入階層）`
                    : "これより前の月は指定できません"
                }
                onClick={() => void appendMonthAll("prev")}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                前月を追加
              </button>
              <button
                type="button"
                disabled={nextDisabled}
                title={
                  nextEdge
                    ? `全ブロックに ${nextEdge} を追加（得意先・全仕入階層）`
                    : "これより後の月は指定できません"
                }
                onClick={() => void appendMonthAll("next")}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                次月を追加
              </button>
            </div>
            <GonenKukumiExcelExportButton
              oracle={initialOracle}
              params={initialParams}
              multiMonth={{ months: excelMultiMonthSlices }}
            />
          </div>
        </div>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-600 md:grid-cols-3">
          <div>
            <dt className="text-slate-500">得意先</dt>
            <dd>{custDisplay}</dd>
          </div>
          <div>
            <dt className="text-slate-500">得意先品目</dt>
            <dd>{initialParams.custItem}</dd>
          </div>
          <div>
            <dt className="text-slate-500">品目任意変換値</dt>
            <dd>{initialParams.optionChange}</dd>
          </div>
          <div>
            <dt className="text-slate-500">検索年月（基準）</dt>
            <dd>{baseYm}</dd>
          </div>
          <div>
            <dt className="text-slate-500">対象日付</dt>
            <dd>{initialParams.asOfDate}</dd>
          </div>
          <div>
            <dt className="text-slate-500">内作品番</dt>
            <dd className="font-mono text-slate-900">{initialOracle.internalItemCd}</dd>
          </div>
        </dl>
      </section>

      <div className="space-y-8">
        {panelSegments.map((segment) => {
          const theme = segmentSectionTheme(segment, bannerOracle);
          const segKey = panelSegmentKey(segment);

          return (
            <section
              key={segKey}
              className="overflow-hidden rounded-lg bg-white"
              style={{
                // border では角で欠けやすいので、角に追従する ring 相当の box-shadow を使う
                boxShadow: `0 0 0 2px ${theme.cssOuterBorder}, 0 1px 2px 0 rgb(0 0 0 / 0.05)`,
              }}
            >
              <div
                className="border-b px-4 py-3"
                style={{ backgroundColor: theme.cssBg, borderColor: theme.cssBorder }}
              >
                {segment.kind === "cust" && segment.filter ? (() => {
                    const b = findCustomerBlock(bannerOracle.customerBlocks, segment.filter);
                    return b ? (
                      <CustomerBannerHeader block={b} />
                    ) : (
                      <span className="text-sm text-slate-600">基準月に該当の得意先行がありません</span>
                    );
                  })() : null}
                {segment.kind === "sup" && segment.filter ? (() => {
                    const block = findSupplierBlock(bannerOracle.supplierBlocks, segment.filter);
                    return block ? (
                      <SupplierBannerHeader block={block} />
                    ) : (
                      <span className="text-sm text-slate-600">基準月に該当の仕入先行がありません</span>
                    );
                  })() : null}
              </div>
              <div className="space-y-2 p-3">
                {sortedLoadedMonths.map((ym) => {
                  const oracle = oracleCache[ym];
                  if (!oracle) {
                    return (
                      <p key={ym} className="text-sm text-amber-800">
                        {ym} のデータを読み込めませんでした。
                      </p>
                    );
                  }
                  const openKey = `${segKey}:${ym}`;
                  const isBase = ym === baseYm;
                  return (
                    <details
                      key={openKey}
                      className="group overflow-hidden rounded-md"
                      style={{
                        boxShadow: `0 0 0 2px ${theme.cssOuterBorder}`,
                        backgroundColor: theme.cssBg,
                      }}
                      open={openMap[openKey] ?? ym === baseYm}
                      onToggle={(e) => {
                        const isOpen = e.currentTarget.open;
                        setOpenMap((m) => ({ ...m, [openKey]: isOpen }));
                      }}
                    >
                      <summary
                        className="flex cursor-pointer list-none items-center justify-between gap-2 border-b px-3 py-2 text-sm font-medium text-slate-800 marker:hidden [&::-webkit-details-marker]:hidden"
                        style={{
                          backgroundColor: theme.cssBg,
                          borderBottomColor: theme.cssBorder,
                        }}
                      >
                        <span>
                          検索年月 <span className="font-semibold tabular-nums">{ym}</span>
                          {isBase ? (
                            <span className="ml-2 font-normal text-slate-600">（基準）</span>
                          ) : null}
                        </span>
                        <span className="shrink-0 text-xs font-normal text-slate-600 group-open:hidden">
                          クリックで展開
                        </span>
                        <span className="hidden shrink-0 text-xs font-normal text-slate-600 group-open:inline">
                          クリックで折りたたみ
                        </span>
                      </summary>
                      <div
                        className="border-t px-1 pb-3 pt-2"
                        style={{
                          borderTopColor: theme.cssBorder,
                          backgroundColor: "white",
                        }}
                      >
                        <GonenKukumiOracleMonthPanels
                          segment={segment}
                          oracle={oracle}
                          params={{ ...initialParams, yearMonth: ym }}
                        />
                      </div>
                    </details>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
