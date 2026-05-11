import { NextResponse } from "next/server";
import { runGonenKukumiOracleSearch } from "@/infrastructure/oracle/gonenkukumi/run-search";
import {
  gonenOracleFailureResponse,
  parseGonenKukumiAuthenticatedSearchPost,
} from "@/app/api/gonenkukumi/parse-search-post";

/**
 * 5年9組 結果の追加表示用。Oracle の生データを JSON で返す（検索履歴は記録しない）。
 */
export async function POST(req: Request) {
  const parsed = await parseGonenKukumiAuthenticatedSearchPost(req);
  if (!parsed.ok) {
    return parsed.response;
  }

  const oracle = await runGonenKukumiOracleSearch(parsed.input);
  if (!oracle.ok) {
    return gonenOracleFailureResponse(oracle);
  }

  return NextResponse.json({ ok: true as const, oracle });
}
