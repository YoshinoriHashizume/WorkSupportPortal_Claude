/** 帯・見出し用の BOM 階層（1 以上の整数） */
export function supplierKaisoForBanner(block: { kaiso?: number }): number {
  return Math.max(1, Math.floor(Number(block.kaiso ?? 1)));
}

/**
 * Oracle が付ける `品目 (階層)` 形式の末尾 ` (n)` を除いた品目表示。
 * 階層は別表示（帯右隅など）に回すとき用。
 */
export function supplierItemCdWithoutLevelParen(itemCdWithLevel: string): string {
  return itemCdWithLevel.replace(/\s*\(\d+\)\s*$/, "").trim();
}
