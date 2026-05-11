import { NextResponse } from "next/server";
import { prisma } from "@/infrastructure/persistence/prisma/client";
import { runGonenKukumiOracleSearch } from "@/infrastructure/oracle/gonenkukumi/run-search";
import {
  gonenOracleFailureResponse,
  parseGonenKukumiAuthenticatedSearchPost,
} from "@/app/api/gonenkukumi/parse-search-post";

export async function POST(req: Request) {
  const parsed = await parseGonenKukumiAuthenticatedSearchPost(req);
  if (!parsed.ok) {
    return parsed.response;
  }
  const { userId, input } = parsed;

  const oracle = await runGonenKukumiOracleSearch(input);
  if (!oracle.ok) {
    return gonenOracleFailureResponse(oracle);
  }

  await prisma.gonenKukumiSearchHistory.create({
    data: {
      userId,
      custCode: input.custCode,
      custItem: input.custItem,
      optionChange: input.optionChange,
      yearMonth: input.yearMonth,
    },
  });

  return NextResponse.json({ ok: true });
}
