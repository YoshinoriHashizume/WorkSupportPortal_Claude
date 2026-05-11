"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

/**
 * 入力＋候補 listbox の「外クリックで閉じる」「Arrow / Enter / Escape のキー操作」
 * を集約したカスタムフック。
 *
 * combobox / autocomplete のどちらでも同じ操作になるため、
 * 個別コンポーネントから内部状態（`open` / `highlight`）と
 * 「外周 div の ref」「キーイベントハンドラ」だけ受け取れば組み立てられる。
 */
export function useListboxPopup<TItem>(itemCount: number): {
  open: boolean;
  setOpen: (v: boolean) => void;
  highlight: number;
  setHighlight: React.Dispatch<React.SetStateAction<number>>;
  close: () => void;
  wrapRef: RefObject<HTMLDivElement | null>;
  listRef: RefObject<HTMLUListElement | null>;
  onInputKeyDown: (
    e: React.KeyboardEvent<HTMLInputElement>,
    onPickIndex: (index: number) => void,
    opts?: { onEnter?: () => boolean },
  ) => void;
  /** 候補配列を引き取って Enter で確定するキーハンドラ生成（簡易版） */
  onInputKeyDownWith: (
    items: readonly TItem[],
    onPick: (item: TItem) => void,
  ) => (e: React.KeyboardEvent<HTMLInputElement>) => void;
} {
  const [open, setOpenRaw] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);

  const close = useCallback(() => {
    setOpenRaw(false);
    setHighlight(-1);
  }, []);

  const setOpen = useCallback((v: boolean) => {
    setOpenRaw(v);
    if (!v) setHighlight(-1);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      const el = wrapRef.current;
      if (el && e.target instanceof Node && !el.contains(e.target)) close();
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open, close]);

  useEffect(() => {
    if (!open || highlight < 0 || !listRef.current) return;
    const li = listRef.current.children[highlight] as HTMLElement | undefined;
    li?.scrollIntoView({ block: "nearest" });
  }, [open, highlight]);

  const onInputKeyDown = useCallback(
    (
      e: React.KeyboardEvent<HTMLInputElement>,
      onPickIndex: (index: number) => void,
      opts?: { onEnter?: () => boolean },
    ) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (!open) {
          setOpenRaw(true);
          setHighlight(itemCount > 0 ? 0 : -1);
        } else {
          setHighlight((h) => {
            if (itemCount === 0) return -1;
            return h < 0 ? 0 : Math.min(h + 1, itemCount - 1);
          });
        }
      } else if (e.key === "ArrowUp" && open) {
        e.preventDefault();
        setHighlight((h) => {
          if (itemCount === 0) return -1;
          if (h <= 0) return 0;
          return h - 1;
        });
      } else if (e.key === "Enter") {
        if (opts?.onEnter?.()) {
          e.preventDefault();
          return;
        }
        if (open && highlight >= 0 && highlight < itemCount) {
          e.preventDefault();
          onPickIndex(highlight);
        }
      } else if (e.key === "Escape" && open) {
        e.preventDefault();
        close();
      }
    },
    [open, highlight, itemCount, close],
  );

  const onInputKeyDownWith = useCallback(
    (items: readonly TItem[], onPick: (item: TItem) => void) =>
      (e: React.KeyboardEvent<HTMLInputElement>) => {
        onInputKeyDown(e, (i) => {
          const item = items[i];
          if (item !== undefined) onPick(item);
        });
      },
    [onInputKeyDown],
  );

  return { open, setOpen, highlight, setHighlight, close, wrapRef, listRef, onInputKeyDown, onInputKeyDownWith };
}
