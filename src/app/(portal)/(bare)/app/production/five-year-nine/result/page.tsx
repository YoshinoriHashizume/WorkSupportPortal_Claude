import { auth } from "@/auth";
import { custHeadlineFromOracle } from "@/domains/gonenkukumi/cust-headline";
import type { GonenKukumiSearchInput } from "@/domains/gonenkukumi/schemas";
import { gonenKukumiSearchParamsFromFlatRecord } from "@/domains/gonenkukumi/search-params-from-url";
import { runGonenKukumiOracleSearch } from "@/infrastructure/oracle/gonenkukumi/run-search";
import { GonenKukumiResultView } from "@/components/gonenkukumi/result-view";
import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { cache } from "react";

/** generateMetadata とページ本体で Oracle を二重に叩かない */
const runGonenKukumiOracleSearchCached = cache(async (input: GonenKukumiSearchInput) =>
  runGonenKukumiOracleSearch(input),
);

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<Metadata> {
  const session = await auth();
  if (!session?.user?.id) {
    return { title: "検索結果" };
  }
  const sp = await searchParams;
  const parsed = gonenKukumiSearchParamsFromFlatRecord(sp);
  if (!parsed.success) {
    return { title: "検索結果" };
  }
  let oracle;
  try {
    oracle = await runGonenKukumiOracleSearchCached(parsed.data);
  } catch {
    return { title: "検索結果" };
  }
  const head = custHeadlineFromOracle(parsed.data.custCode, oracle);
  return { title: `${head}：${parsed.data.custItem}` };
}

export default async function GonenKukumiResultPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/login");
  }

  const sp = await searchParams;
  const parsed = gonenKukumiSearchParamsFromFlatRecord(sp);
  if (!parsed.success) {
    notFound();
  }

  const input = parsed.data;
  let oracle;
  try {
    oracle = await runGonenKukumiOracleSearchCached(input);
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return (
      <GonenKukumiResultView
        oracle={{
          ok: false,
          code: "ORACLE_ERROR",
          message: `サーバー処理でエラーが発生しました: ${message}`,
        }}
        params={{
          custCode: input.custCode,
          custItem: input.custItem,
          optionChange: input.optionChange,
          yearMonth: input.yearMonth,
          asOfDate: input.asOfDate,
        }}
      />
    );
  }

  return (
    <GonenKukumiResultView
      oracle={oracle}
      params={{
        custCode: input.custCode,
        custItem: input.custItem,
        optionChange: input.optionChange,
        yearMonth: input.yearMonth,
        asOfDate: input.asOfDate,
      }}
    />
  );
}
