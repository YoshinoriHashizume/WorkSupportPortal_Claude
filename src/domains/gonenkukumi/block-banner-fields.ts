import {
  gonenConsTypLabel,
  gonenQtyBannerJa,
} from "@/domains/gonenkukumi/gonen-display-format";
import {
  supplierItemCdWithoutLevelParen,
  supplierKaisoForBanner,
} from "@/domains/gonenkukumi/supplier-banner-text";
import type {
  CustomerShipBlock,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";

/**
 * バナー帯の 1 フィールド。
 * `label` を持つときは "ラベル：値" 表記、無ければ `text` だけを単独で表示する。
 */
export type GonenBannerField = {
  /** "得意先品目" など。primary 行は省略 */
  label?: string;
  /** 値テキスト（数値も整形済みの文字列） */
  text: string;
  /** Web で値部分を等幅にする (品目コード等) */
  mono?: boolean;
};

export type CustomerBanner = {
  /** "得意先：{name}（{code}） 出荷" 等の見出し */
  primary: GonenBannerField;
  rest: GonenBannerField[];
};

export type SupplierBanner = {
  /** "仕入先：{name}（{code}） 入荷" 等の見出し */
  primary: GonenBannerField;
  /** "階層 {n}" 等の右側固定情報（Web は右寄せ、Excel は primary の次に連結） */
  aside: GonenBannerField;
  rest: GonenBannerField[];
};

export function customerBannerOf(block: CustomerShipBlock): CustomerBanner {
  return {
    primary: { text: `得意先：${block.custName}（${block.custCode}） 出荷` },
    rest: [
      { label: "得意先品目", text: block.custItemCd, mono: true },
      { label: "手番", text: String(block.teban) },
      { label: "安全在庫", text: gonenQtyBannerJa(block.anzen) },
    ],
  };
}

export function supplierBannerOf(block: SupplierBlock): SupplierBanner {
  return {
    primary: { text: `仕入先：${block.vendName}（${block.vendCode}） 入荷` },
    aside: { text: `階層 ${supplierKaisoForBanner(block)}` },
    rest: [
      {
        label: "品目番号",
        text: supplierItemCdWithoutLevelParen(block.itemCdWithLevel),
        mono: true,
      },
      { label: "手配区分", text: block.arrangementTyp || "—" },
      { label: "保管区", text: block.whCd },
      { label: "支給区分", text: gonenConsTypLabel(block.consTyp) },
      { label: "最上位品番", text: block.topItemCd, mono: true },
      { label: "手番", text: String(block.teban) },
      { label: "安全在庫", text: gonenQtyBannerJa(block.anzen) },
    ],
  };
}

function fieldText(f: GonenBannerField): string {
  return f.label ? `${f.label}：${f.text}` : f.text;
}

/** Excel など平文の 1 行表現（全角スペース連結。Web 表示と完全に同じ並び・文言） */
export function customerBannerLine(block: CustomerShipBlock): string {
  const b = customerBannerOf(block);
  return [fieldText(b.primary), ...b.rest.map(fieldText)].join("　");
}

export function supplierBannerLine(block: SupplierBlock): string {
  const b = supplierBannerOf(block);
  return [fieldText(b.primary), fieldText(b.aside), ...b.rest.map(fieldText)].join("　");
}
