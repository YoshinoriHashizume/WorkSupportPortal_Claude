/** 表セル用：0 と null/undefined は空欄 */
export function gonenQtyCellJa(v: number | null | undefined): string {
  if (v == null || v === 0) return "";
  return Number(v).toLocaleString("ja-JP");
}

/** バナー帯（安全在庫など）用：0 はそのまま "0" を表示する */
export function gonenQtyBannerJa(v: number | null | undefined): string {
  if (v == null) return "";
  return Number(v).toLocaleString("ja-JP");
}

export function gonenConsTypLabel(v: number | null | undefined): string {
  const n = Number(v ?? 0);
  if (n === 1) return "有償支給";
  if (n === 2) return "無償支給";
  return "非";
}

/** 仕入ブロックの階層インデックス（1 始まり、最低 1） */
export function gonenSupplierKaisoFloor(kaiso: number | null | undefined): number {
  return Math.max(1, Math.floor(Number(kaiso ?? 1)));
}
