"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  align?: "left" | "right";
  className?: string;
  /** これ以下には縮めない（極端に長い値ははみ出し得る） */
  minPx?: number;
};

/**
 * 親の table セル（td/th）の内容幅に収まるよう、必要なときだけ font-size を下げる。
 * 画面（viewport）ではなくセル幅ベース。
 */
export function GonenkukumiCellFit({
  children,
  align = "left",
  className = "",
  minPx = 7,
}: Props) {
  const ref = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const span = ref.current;
    if (!span) return;
    const cell = span.parentElement;
    if (!cell || (cell.tagName !== "TD" && cell.tagName !== "TH")) return;

    const fit = () => {
      span.style.removeProperty("font-size");
      const cs = getComputedStyle(cell);
      const pl = parseFloat(cs.paddingLeft) || 0;
      const pr = parseFloat(cs.paddingRight) || 0;
      const available = cell.clientWidth - pl - pr - 2;
      if (available <= 1) return;

      const basePx = parseFloat(getComputedStyle(span).fontSize) || 14;
      span.style.fontSize = `${basePx}px`;

      if (span.scrollWidth <= available) return;

      let next = Math.max(minPx, basePx * (available / span.scrollWidth) * 0.97);
      span.style.fontSize = `${next}px`;

      if (span.scrollWidth > available && next > minPx) {
        next = Math.max(minPx, next * (available / span.scrollWidth) * 0.98);
        span.style.fontSize = `${next}px`;
      }
    };

    const ro = new ResizeObserver(fit);
    ro.observe(cell);
    fit();

    return () => ro.disconnect();
  }, [children, minPx]);

  const alignClass = align === "right" ? "text-right" : "text-left";

  return (
    <span
      ref={ref}
      className={`inline-block max-w-full whitespace-nowrap [font-size:inherit] ${alignClass} ${className}`.trim()}
    >
      {children}
    </span>
  );
}
