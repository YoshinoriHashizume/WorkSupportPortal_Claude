export type KaisoColor = {
  /** CSS: hsl(...) */
  cssBg: string;
  /** CSS: hsl(...)（薄い背景） */
  cssLightBg: string;
  /** CSS: hsl(...)（ほぼ白の背景：帯の区切り等） */
  cssVeryLightBg: string;
  /** CSS: hsl(...) */
  cssBorder: string;
  /** CSS: hsl(...)（外枠用：少し濃い） */
  cssOuterBorder: string;
  /** Excel: "FFRRGGBB" */
  excelArgbBg: string;
  /** Excel: "FFRRGGBB"（薄い背景） */
  excelArgbLightBg: string;
  /** Excel: "FFRRGGBB"（ほぼ白の背景：帯の区切り等） */
  excelArgbVeryLightBg: string;
  /** Excel: "FFRRGGBB"（タイトル・日付行などの枠用：少し薄い） */
  excelArgbBorder: string;
  /** Excel: "FFRRGGBB"（外枠用：少し濃い） */
  excelArgbOuterBorder: string;
};

function clamp01(x: number): number {
  return Math.min(1, Math.max(0, x));
}

function hueFromKaiso(kaiso: number, h0 = 200): number {
  const k = Number.isFinite(kaiso) ? Math.max(1, Math.floor(kaiso)) : 1;
  const golden = 137.508;
  const h = (h0 + (k - 1) * golden) % 360;
  return h < 0 ? h + 360 : h;
}

// HSL → RGB (0..255)
function hslToRgb(h: number, s: number, l: number): { r: number; g: number; b: number } {
  const hh = ((h % 360) + 360) % 360;
  const ss = clamp01(s);
  const ll = clamp01(l);
  const c = (1 - Math.abs(2 * ll - 1)) * ss;
  const x = c * (1 - Math.abs(((hh / 60) % 2) - 1));
  const m = ll - c / 2;
  let r1 = 0;
  let g1 = 0;
  let b1 = 0;
  if (hh < 60) [r1, g1, b1] = [c, x, 0];
  else if (hh < 120) [r1, g1, b1] = [x, c, 0];
  else if (hh < 180) [r1, g1, b1] = [0, c, x];
  else if (hh < 240) [r1, g1, b1] = [0, x, c];
  else if (hh < 300) [r1, g1, b1] = [x, 0, c];
  else [r1, g1, b1] = [c, 0, x];
  const r = Math.round((r1 + m) * 255);
  const g = Math.round((g1 + m) * 255);
  const b = Math.round((b1 + m) * 255);
  return { r, g, b };
}

function toHex2(n: number): string {
  const x = Math.max(0, Math.min(255, Math.round(n)));
  return x.toString(16).toUpperCase().padStart(2, "0");
}

function rgbToArgbHex(rgb: { r: number; g: number; b: number }): string {
  return `FF${toHex2(rgb.r)}${toHex2(rgb.g)}${toHex2(rgb.b)}`;
}

/**
 * 階層番号→色（同じ色は再利用しない）
 * - Hue は黄金角で分散
 * - 背景は淡色、枠は少し濃いめ
 */
export function kaisoColor(kaiso: number): KaisoColor {
  const h = hueFromKaiso(kaiso, 200); // 1 は水色系から開始
  const bg = `hsl(${h.toFixed(3)} 55% 92%)`;
  const lightBg = `hsl(${h.toFixed(3)} 45% 96%)`;
  const veryLightBg = `hsl(${h.toFixed(3)} 25% 98%)`;
  const border = `hsl(${h.toFixed(3)} 45% 75%)`;
  const outerBorder = `hsl(${h.toFixed(3)} 55% 55%)`;
  const rgbBg = hslToRgb(h, 0.55, 0.92);
  const rgbLightBg = hslToRgb(h, 0.45, 0.96);
  const rgbVeryLightBg = hslToRgb(h, 0.25, 0.98);
  const rgbBorder = hslToRgb(h, 0.45, 0.75);
  const rgbOuter = hslToRgb(h, 0.55, 0.55);
  return {
    cssBg: bg,
    cssLightBg: lightBg,
    cssVeryLightBg: veryLightBg,
    cssBorder: border,
    cssOuterBorder: outerBorder,
    excelArgbBg: rgbToArgbHex(rgbBg),
    excelArgbLightBg: rgbToArgbHex(rgbLightBg),
    excelArgbVeryLightBg: rgbToArgbHex(rgbVeryLightBg),
    excelArgbBorder: rgbToArgbHex(rgbBorder),
    excelArgbOuterBorder: rgbToArgbHex(rgbOuter),
  };
}

