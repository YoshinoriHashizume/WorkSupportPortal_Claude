import type {
  CustomerShipBlock,
  GonenKukumiOracleSuccess,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";
import type { GonenPanelSegment } from "@/domains/gonenkukumi/panel-segments";

export type CustomerBlockFilter = {
  custCode: string;
  custItemCd: string;
  teban: number;
};

export type SupplierBlockFilter = {
  vendCode: string;
  itemCdWithLevel: string;
};

export function findCustomerBlock(
  blocks: readonly CustomerShipBlock[],
  filter: CustomerBlockFilter,
): CustomerShipBlock | undefined {
  return blocks.find(
    (b) =>
      b.custCode === filter.custCode &&
      b.custItemCd === filter.custItemCd &&
      Number(b.teban) === Number(filter.teban),
  );
}

export function findSupplierBlock(
  blocks: readonly SupplierBlock[],
  filter: SupplierBlockFilter,
): SupplierBlock | undefined {
  return blocks.find(
    (b) => b.vendCode === filter.vendCode && b.itemCdWithLevel === filter.itemCdWithLevel,
  );
}

export function findCustomerBlockBySegment(
  oracle: GonenKukumiOracleSuccess,
  segment: Extract<GonenPanelSegment, { kind: "cust" }>,
): CustomerShipBlock | undefined {
  if (!segment.filter) return undefined;
  return findCustomerBlock(oracle.customerBlocks, segment.filter);
}

export function findSupplierBlockBySegment(
  oracle: GonenKukumiOracleSuccess,
  segment: Extract<GonenPanelSegment, { kind: "sup" }>,
): SupplierBlock | undefined {
  if (!segment.filter) return undefined;
  return findSupplierBlock(oracle.supplierBlocks, segment.filter);
}
