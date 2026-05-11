import { gonenKukumiSearchSchema } from "@/domains/gonenkukumi/schemas";

export function firstString(v: string | string[] | undefined): string | undefined {
  if (v == null) return undefined;
  return Array.isArray(v) ? v[0] : v;
}

export function gonenKukumiSearchParamsFromFlatRecord(
  sp: Record<string, string | string[] | undefined>,
) {
  const raw = {
    custCode: firstString(sp.custCode) ?? "",
    custItem: firstString(sp.custItem) ?? "",
    optionChange: firstString(sp.optionChange)?.trim() || "*",
    yearMonth: firstString(sp.yearMonth) ?? "",
    asOfDate: firstString(sp.asOfDate) ?? "",
  };
  return gonenKukumiSearchSchema.safeParse(raw);
}
