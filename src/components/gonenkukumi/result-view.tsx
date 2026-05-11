import type { GonenKukumiOracleResult } from "@/domains/gonenkukumi/types";
import { GonenKukumiMultiMonthResultClient } from "@/components/gonenkukumi/gonenkukumi-multi-month-result-client";
import type { GonenKukumiResultPanelParams } from "@/components/gonenkukumi/gonenkukumi-oracle-month-panels";

export function GonenKukumiResultView({
  oracle,
  params,
}: {
  oracle: GonenKukumiOracleResult;
  params: GonenKukumiResultPanelParams;
}) {
  if (!oracle.ok) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-medium">{oracle.message}</p>
        {oracle.code === "ORACLE_NOT_CONFIGURED" && (
          <p className="mt-2 text-amber-800">
            開発時は `.env.local` に `ORACLE_PASSWORD` を設定してください。
          </p>
        )}
      </div>
    );
  }

  return <GonenKukumiMultiMonthResultClient initialOracle={oracle} initialParams={params} />;
}
