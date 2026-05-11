import {
  findCustomerBlock,
  findSupplierBlock,
} from "@/domains/gonenkukumi/block-finders";
import type { GonenPanelSegment } from "@/domains/gonenkukumi/panel-segments";
import type { GonenKukumiOracleSuccess } from "@/domains/gonenkukumi/types";
import {
  CustomerBannerHeader,
  SupplierBannerHeader,
} from "@/components/gonenkukumi/block-banner-header";

/**
 * セグメント（得意先 / 仕入先 + filter）に応じた帯見出しを描画する。
 * 該当ブロックが見つからないときは `fallback` 文言を `<span>` で表示する。
 *
 * gonenkukumi-multi-month-result-client / gonenkukumi-oracle-month-panels で
 * 重複していた「kind と filter の組み合わせで CustomerBannerHeader /
 * SupplierBannerHeader を出し分ける」処理を 1 か所に集約する。
 */
export function SegmentBannerHeader({
  segment,
  banner,
  fallbackCustomer = "基準月に該当の得意先行がありません",
  fallbackSupplier = "基準月に該当の仕入先行がありません",
  fallbackClassName = "text-sm text-slate-600",
}: {
  segment: GonenPanelSegment;
  banner: GonenKukumiOracleSuccess;
  fallbackCustomer?: string;
  fallbackSupplier?: string;
  fallbackClassName?: string;
}) {
  if (segment.kind === "cust" && segment.filter) {
    const b = findCustomerBlock(banner.customerBlocks, segment.filter);
    return b ? (
      <CustomerBannerHeader block={b} />
    ) : (
      <span className={fallbackClassName}>{fallbackCustomer}</span>
    );
  }
  if (segment.kind === "sup" && segment.filter) {
    const block = findSupplierBlock(banner.supplierBlocks, segment.filter);
    return block ? (
      <SupplierBannerHeader block={block} />
    ) : (
      <span className={fallbackClassName}>{fallbackSupplier}</span>
    );
  }
  return null;
}
