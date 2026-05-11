"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type CustOption = { custCode: string; custName: string };

type Props = {
  value: string;
  onChange: (custCode: string) => void;
  disabled?: boolean;
};

function norm(s: string): string {
  return s.trim().toLowerCase();
}

function matches(opt: CustOption, query: string): boolean {
  if (!query) return true;
  const q = norm(query);
  return norm(opt.custCode).includes(q) || norm(opt.custName).includes(q);
}

export function CustCodeCombobox({ value, onChange, disabled }: Props) {
  const [options, setOptions] = useState<CustOption[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const wrapRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/gonenkukumi/customers");
        const raw = await res.text();
        if (!res.ok) {
          if (!cancelled) setLoadError("得意先一覧の取得に失敗しました。");
          return;
        }
        const data = JSON.parse(raw) as { items?: CustOption[]; loadError?: string };
        if (!cancelled) {
          setOptions(Array.isArray(data.items) ? data.items : []);
          setLoadError(typeof data.loadError === "string" ? data.loadError : null);
        }
      } catch {
        if (!cancelled) setLoadError("得意先一覧の取得に失敗しました。");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    return options.filter((o) => matches(o, value));
  }, [options, value]);

  const close = useCallback(() => {
    setOpen(false);
    setHighlight(-1);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      const el = wrapRef.current;
      if (el && !el.contains(e.target as Node)) close();
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open, close]);

  useEffect(() => {
    if (!open || highlight < 0 || !listRef.current) return;
    const li = listRef.current.children[highlight] as HTMLElement | undefined;
    li?.scrollIntoView({ block: "nearest" });
  }, [open, highlight]);

  function pick(code: string) {
    onChange(code);
    close();
    inputRef.current?.focus();
  }

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (disabled) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) {
        setOpen(true);
        setHighlight(filtered.length > 0 ? 0 : -1);
      } else {
        setHighlight((h) => {
          if (filtered.length === 0) return -1;
          return h < 0 ? 0 : Math.min(h + 1, filtered.length - 1);
        });
      }
    } else if (e.key === "ArrowUp" && open) {
      e.preventDefault();
      setHighlight((h) => {
        if (filtered.length === 0) return -1;
        if (h <= 0) return 0;
        return h - 1;
      });
    } else if (e.key === "Enter" && open && highlight >= 0 && filtered[highlight]) {
      e.preventDefault();
      pick(filtered[highlight].custCode);
    } else if (e.key === "Escape" && open) {
      e.preventDefault();
      close();
    }
  }

  const listId = "gonenkukumi-cust-code-listbox";

  return (
    <div ref={wrapRef} className="relative">
      <div className="flex gap-1">
        <input
          ref={inputRef}
          id="gonenkukumi-cust-code"
          name="custCode"
          required
          autoComplete="off"
          disabled={disabled}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setHighlight(-1);
          }}
          onFocus={() => {
            setOpen(true);
          }}
          onKeyDown={onInputKeyDown}
          role="combobox"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          aria-autocomplete="list"
          className="mt-1 min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 font-mono text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
        />
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            setOpen((o) => !o);
            if (!open) setHighlight(filtered.length > 0 ? 0 : -1);
          }}
          className="mt-1 shrink-0 rounded-md border border-slate-300 bg-slate-50 px-2.5 py-2 text-slate-600 shadow-sm hover:bg-slate-100 disabled:opacity-50"
          aria-label="得意先一覧を開く"
        >
          ▼
        </button>
      </div>
      {loadError && (
        <p className="mt-1 text-xs text-amber-700" role="status">
          {loadError}（コードを直接入力して検索できます）
        </p>
      )}
      {open && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-48 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg"
        >
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-slate-500" role="presentation">
              {options.length === 0 ? "候補がありません" : "一致する候補がありません"}
            </li>
          ) : (
            filtered.map((opt, i) => (
              <li
                key={opt.custCode}
                role="option"
                aria-selected={i === highlight}
                className={`cursor-pointer px-3 py-1.5 font-mono text-slate-900 ${
                  i === highlight ? "bg-sky-100" : "hover:bg-slate-50"
                }`}
                onMouseEnter={() => setHighlight(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(opt.custCode);
                }}
              >
                <span className="font-medium">{opt.custCode}</span>
                <span className="ml-2 text-xs text-slate-500">{opt.custName}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
