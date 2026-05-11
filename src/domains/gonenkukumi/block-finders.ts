import type { CustomerShipBlock, SupplierBlock } from "@/domains/gonenkukumi/types";

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
