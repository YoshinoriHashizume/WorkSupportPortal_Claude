"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

const MAX_LEN = 200;
const MAX_SHOW = 1000;

type CacheKey = `${string}\x1f${string}`;
type CacheEntry = { items: string[]; fetchedAt: number };
const custItemCache = new Map<CacheKey, CacheEntry>();

type Props = {
  id?: string;
  value: string;
  onChange: (v: string) => void;
  custCode: string;
  asOfDate: string;
  disabled?: boolean;
};

export function CustItemAutocompleteInput({ id, value, onChange, custCode, asOfDate, disabled }: Props) {
  const reactId = useId();
  const listboxId = `${reactId}-listbox`;
  const inputId = id ?? `${reactId}-input`;

  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [allItems, setAllItems] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchHint, setFetchHint] = useState<string | null>(null);
  /** 直近の検索が成功し、候補が 0 件だった */
  const [noMatchingItems, setNoMatchingItems] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const wrapRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setHighlight(-1);
  }, []);

  const cacheKey = useMemo(() => {
    // 得意先コードが「191/」等で崩れても、数字3桁に正規化して扱う
    const cc = custCode.replace(/\D/g, "").trim();
    const d = asOfDate.trim();
    return cc.length === 3 && d ? (`${cc}\x1f${d}` as CacheKey) : null;
  }, [custCode, asOfDate]);

  useEffect(() => {
    abortRef.current?.abort();
    abortRef.current = null;

    if (disabled || !cacheKey) {
      setSuggestions([]);
      setAllItems(null);
      setLoading(false);
      setFetchHint(null);
      setNoMatchingItems(false);
      close();
      return;
    }

    const existing = custItemCache.get(cacheKey);
    if (existing) {
      setAllItems(existing.items);
      setLoading(false);
      setFetchHint(null);
      return;
    }

    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setAllItems(null);
    setFetchHint(null);
    setNoMatchingItems(false);
    close();

    const [cc, d] = cacheKey.split("\x1f");
    const qs = new URLSearchParams({ custCode: cc ?? "", asOfDate: d ?? "" });
    void (async () => {
      try {
        const res = await fetch(`/api/gonenkukumi/cust-items?${qs}`, {
          signal: ac.signal,
          credentials: "same-origin",
        });
        const data: unknown = await res.json().catch(() => ({}));
        if (ac.signal.aborted) return;
        if (!res.ok) {
          if (res.status === 401) {
            setFetchHint("候補を取得するにはログインが必要です。");
          } else if (res.status === 400) {
            const msg =
              typeof data === "object" && data && "error" in data && typeof (data as { error: unknown }).error === "string"
                ? (data as { error: string }).error
                : "対象日付の形式が不正です。";
            setFetchHint(msg);
          } else {
            setFetchHint("候補の取得に失敗しました。しばらくしてから再度お試しください。");
          }
          return;
        }
        const list =
          typeof data === "object" && data && "items" in data && Array.isArray((data as { items: unknown }).items)
            ? ((data as { items: string[] }).items ?? []).filter((s) => typeof s === "string")
            : [];
        custItemCache.set(cacheKey, { items: list, fetchedAt: Date.now() });
        setAllItems(list);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setFetchHint("候補の取得に失敗しました。");
      } finally {
        if (!ac.signal.aborted) setLoading(false);
      }
    })();

    return () => {
      abortRef.current?.abort();
    };
  }, [cacheKey, disabled, close]);

  // 入力1文字ごとにローカル候補を表示（通信なし）
  useEffect(() => {
    const q = value.trim();
    if (disabled || !cacheKey) {
      setSuggestions([]);
      setNoMatchingItems(false);
      close();
      return;
    }
    // 履歴反映直後など、全件キャッシュ取得前は「不一致」を出さない
    if (!allItems) {
      setSuggestions([]);
      setNoMatchingItems(false);
      close();
      return;
    }
    if (!q) {
      setSuggestions([]);
      setNoMatchingItems(false);
      close();
      return;
    }
    const pfx = q.slice(0, 40);
    const list = allItems.filter((s) => s.startsWith(pfx)).slice(0, MAX_SHOW);
    setSuggestions(list);
    setOpen(list.length > 0);
    setHighlight(list.length > 0 ? 0 : -1);
    setNoMatchingItems(list.length === 0);
  }, [value, cacheKey, allItems, disabled, close]);

  useEffect(() => {
    function onDocMouseDown(e: MouseEvent) {
      const el = wrapRef.current;
      if (!el || !open) return;
      if (e.target instanceof Node && !el.contains(e.target)) close();
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open, close]);

  const pick = useCallback(
    (s: string) => {
      onChange(s);
      close();
    },
    [onChange, close],
  );

  return (
    <div ref={wrapRef} className="relative mt-1">
      <input
        id={inputId}
        name="custItem"
        required
        autoComplete="off"
        spellCheck={false}
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, MAX_LEN))}
        onFocus={() => {
          if (suggestions.length > 0) setOpen(true);
        }}
        onKeyDown={(e) => {
          if (!open || suggestions.length === 0) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setHighlight((h) => (h + 1) % suggestions.length);
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setHighlight((h) => (h - 1 + suggestions.length) % suggestions.length);
          } else if (e.key === "Enter" && highlight >= 0 && highlight < suggestions.length) {
            e.preventDefault();
            pick(suggestions[highlight]!);
          } else if (e.key === "Escape") {
            close();
          }
        }}
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listboxId}
        className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
      />
      {open && suggestions.length > 0 ? (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute z-[100] mt-1 max-h-48 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg"
        >
          {suggestions.map((s, i) => (
            <li
              key={s}
              role="option"
              aria-selected={i === highlight}
              className={`cursor-pointer px-3 py-1.5 font-mono text-slate-900 ${i === highlight ? "bg-sky-50" : "hover:bg-slate-50"}`}
              onMouseDown={(ev) => {
                ev.preventDefault();
                pick(s);
              }}
              onMouseEnter={() => setHighlight(i)}
            >
              {s}
            </li>
          ))}
        </ul>
      ) : null}
      {loading ? (
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400">
          …
        </span>
      ) : null}
      {fetchHint ? (
        <p className="mt-1 text-xs text-amber-800" role="status">
          {fetchHint}
        </p>
      ) : null}
      {noMatchingItems && !loading && !fetchHint ? (
        <p className="mt-1 text-xs text-red-600" role="status">
          一致する得意先品目がありません。
        </p>
      ) : null}
    </div>
  );
}
