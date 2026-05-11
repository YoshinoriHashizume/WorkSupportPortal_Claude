import { NextResponse } from "next/server";
import { jsonErrorResponse, requireAuthenticatedUser } from "@/app/api/_lib/require-auth";
import { GONEN_AS_OF_DATE_REGEX } from "@/domains/gonenkukumi/schemas";
import { listGonenKukumiCustItems } from "@/infrastructure/oracle/gonenkukumi/list-cust-items";

/** 得意先品目のプリフェッチ用（全件）。GET ?custCode=&asOfDate= */
export async function GET(req: Request) {
  const guard = await requireAuthenticatedUser();
  if (!guard.ok) return guard.response;

  const { searchParams } = new URL(req.url);
  const custCode = (searchParams.get("custCode") ?? "").trim();
  const asOfDate = (searchParams.get("asOfDate") ?? "").trim();

  if (!custCode) {
    return NextResponse.json({ items: [] as string[] });
  }
  if (!GONEN_AS_OF_DATE_REGEX.test(asOfDate)) {
    return NextResponse.json({ error: "対象日付は yyyy/mm/dd で指定してください" }, { status: 400 });
  }

  try {
    const items = await listGonenKukumiCustItems({ custCode, asOfDate });
    return NextResponse.json({ items });
  } catch (e) {
    return jsonErrorResponse(e, { items: [] as string[] });
  }
}
