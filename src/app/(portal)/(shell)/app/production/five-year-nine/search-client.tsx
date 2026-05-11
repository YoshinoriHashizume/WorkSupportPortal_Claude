"use client";

import { CustCodeCombobox } from "@/components/gonenkukumi/cust-code-combobox";
import { CustItemAutocompleteInput } from "@/components/gonenkukumi/cust-item-autocomplete-input";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  clampYm,
  formatYmJaLabel,
  isoToYmdSlash,
  normalizeYearMonth,
  todayYm,
  todayYmd,
  yearMonthBounds,
  ymdSlashToIso,
  ymOptionsList,
} from "@/domains/gonenkukumi/year-month-nav";
import { TOKYO_TIME_ZONE } from "@/domains/shared/timezone";
import { postJson } from "@/lib/http";

export type HistoryRow = {
  id: string;
  executedAt: string;
  custCode: string;
  custItem: string;
  optionChange: string;
  yearMonth: string;
};

/** SSR / クライアントで同じ文字列になるようタイムゾーンを固定（ハイドレーションずれ防止） */
const executedAtJa = new Intl.DateTimeFormat("ja-JP", {
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
  timeZone: TOKYO_TIME_ZONE,
});

function formatExecutedAt(iso: string): string {
  return executedAtJa.format(new Date(iso));
}

export function GonenKukumiSearchClient({ initialHistory }: { initialHistory: HistoryRow[] }) {
  const router = useRouter();
  const [custCode, setCustCode] = useState("");
  const [custItem, setCustItem] = useState("");
  const [optionChange, setOptionChange] = useState("*");
  const [asOfDate, setAsOfDate] = useState(() => todayYmd());
  const [yearMonth, setYearMonth] = useState(() => {
    const b = yearMonthBounds(todayYmd());
    return clampYm(todayYm(), b.min, b.max);
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const ymBounds = useMemo(() => yearMonthBounds(asOfDate), [asOfDate]);
  const ymOptions = useMemo(() => ymOptionsList(ymBounds.min, ymBounds.max), [ymBounds.min, ymBounds.max]);

  const prevCustCodeRef = useRef<string>("");
  const suppressCustItemClearRef = useRef(false);
  useEffect(() => {
    if (suppressCustItemClearRef.current) {
      suppressCustItemClearRef.current = false;
      prevCustCodeRef.current = custCode;
      return;
    }
    const prev = prevCustCodeRef.current;
    if (prev && prev !== custCode) {
      setCustItem("");
    } else if (!custCode.trim()) {
      setCustItem("");
    }
    prevCustCodeRef.current = custCode;
  }, [custCode]);

  useEffect(() => {
    setYearMonth((prev) => clampYm(prev, ymBounds.min, ymBounds.max));
  }, [ymBounds.min, ymBounds.max]);

  function applyHistoryToForm(h: HistoryRow) {
    suppressCustItemClearRef.current = true;
    setCustCode(h.custCode);
    setCustItem(h.custItem);
    setOptionChange(h.optionChange?.trim() ? h.optionChange : "*");
    const b = yearMonthBounds(asOfDate);
    setYearMonth(clampYm(normalizeYearMonth(h.yearMonth), b.min, b.max));
    setError(null);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await postJson<{ ok?: boolean }>("/api/gonenkukumi/search", {
        custCode,
        custItem,
        optionChange: optionChange || "*",
        yearMonth,
        asOfDate,
      });
      if (!result.ok) {
        setError(result.error);
        return;
      }
      if (result.data.ok) {
        const q = new URLSearchParams({
          custCode,
          custItem,
          optionChange: optionChange || "*",
          yearMonth,
          asOfDate,
        });
        const resultUrl = `/app/production/five-year-nine/result?${q}`;
        const a = document.createElement("a");
        a.href = resultUrl;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        document.body.appendChild(a);
        a.click();
        a.remove();
        router.refresh();
      } else {
        setError("検索は成功したように見えますが、結果画面を開けませんでした。応答を確認してください。");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="grid items-stretch gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <form
          onSubmit={onSubmit}
          className="flex h-full min-h-0 min-w-0 flex-col space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
        <h2 className="text-sm font-semibold text-slate-800">検索条件</h2>
        <div className="min-w-0 flex-1 space-y-4">
          <div className="block text-sm">
            <label htmlFor="gonenkukumi-cust-code" className="text-slate-600">
              得意先コード
            </label>
            <CustCodeCombobox value={custCode} onChange={setCustCode} disabled={loading} />
          </div>
          <div className="block text-sm">
            <label htmlFor="gonenkukumi-cust-item" className="text-slate-600">
              得意先品目
            </label>
            <CustItemAutocompleteInput
              id="gonenkukumi-cust-item"
              value={custItem}
              onChange={setCustItem}
              custCode={custCode}
              asOfDate={asOfDate}
              disabled={loading || !custCode.trim()}
            />
          </div>
          <label className="block text-sm">
            <span className="text-slate-600">品目任意変換値</span>
            <input
              value={optionChange}
              onChange={(e) => setOptionChange(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="*"
            />
          </label>
          <div className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-600">検索年月</span>
              <select
                required
                value={yearMonth}
                onChange={(e) => setYearMonth(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              >
                {ymOptions.map((ym) => (
                  <option key={ym} value={ym}>
                    {formatYmJaLabel(ym)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-slate-600">対象日付</span>
              <input
                type="date"
                required
                value={ymdSlashToIso(asOfDate)}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v) setAsOfDate(isoToYmdSlash(v));
                }}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </label>
          </div>
        </div>
        <div className="mt-auto flex flex-col gap-2 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="self-start rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-sky-700 disabled:opacity-50"
          >
            {loading ? "検索中…" : "検索"}
          </button>
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </div>
          )}
        </div>
        </form>

        <section className="flex h-full min-h-0 min-w-0 flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="shrink-0 text-sm font-semibold text-slate-800">検索履歴</h2>
          <p className="mt-1 shrink-0 text-xs text-slate-500">
            履歴をクリックすると、検索条件にその内容を反映します。
          </p>
          <div className="mt-3 min-h-0 flex-1 overflow-x-auto overflow-y-auto" style={{ maxHeight: "20rem" }}>
            <table className="w-full min-w-[480px] table-fixed border-collapse text-sm lg:min-w-0">
              <thead>
                <tr className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-left text-xs font-medium text-slate-600">
                  <th className="whitespace-nowrap px-1.5 py-1.5 lg:w-1/5">得意先コード</th>
                  <th className="whitespace-nowrap px-1.5 py-1.5 lg:w-1/5">得意先品目</th>
                  <th className="whitespace-nowrap px-1.5 py-1.5 lg:w-1/5">品目任意変換値</th>
                  <th className="whitespace-nowrap px-1.5 py-1.5 lg:w-1/5">検索年月</th>
                  <th className="whitespace-nowrap px-1.5 py-1.5 lg:w-1/5">検索日時</th>
                </tr>
              </thead>
              <tbody>
                {initialHistory.length === 0 ? (
                  <tr>
                    <td className="py-6 text-center text-slate-500" colSpan={5}>
                      まだ履歴がありません。
                    </td>
                  </tr>
                ) : (
                  initialHistory.map((h) => {
                    const opt = h.optionChange?.trim() ? h.optionChange : "*";
                    const label = `検索条件に反映: ${h.custCode} ${h.custItem}`;
                    return (
                      <tr
                        key={h.id}
                        tabIndex={0}
                        role="button"
                        aria-label={label}
                        onClick={() => applyHistoryToForm(h)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            applyHistoryToForm(h);
                          }
                        }}
                        className="cursor-pointer border-b border-slate-100 text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-sky-500 last:border-b-0"
                      >
                        <td className="truncate px-1.5 py-2 font-mono text-slate-900" title={h.custCode}>
                          {h.custCode}
                        </td>
                        <td className="truncate px-1.5 py-2" title={h.custItem}>
                          {h.custItem}
                        </td>
                        <td className="truncate px-1.5 py-2 font-mono">{opt}</td>
                        <td className="truncate px-1.5 py-2">{formatYmJaLabel(normalizeYearMonth(h.yearMonth))}</td>
                        <td className="break-words px-1.5 py-2 text-xs text-slate-500">
                          {formatExecutedAt(h.executedAt)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
