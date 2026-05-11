import { NextResponse } from "next/server";
import { jsonErrorResponse, requireAuthenticatedUser } from "@/app/api/_lib/require-auth";
import { GONEN_AS_OF_DATE_REGEX } from "@/domains/gonenkukumi/schemas";
import { listGonenKukumiCustItemSuggestions } from "@/infrastructure/oracle/gonenkukumi/list-cust-item-suggestions";

/** 得意先品目のオートコンプリート用。GET ?custCode=&q=&asOfDate= （q は 3 文字以上） */
export async function GET(req: Request) {
  const guard = await requireAuthenticatedUser();
  if (!guard.ok) return guard.response;

  const { searchParams } = new URL(req.url);
  const custCode = (searchParams.get("custCode") ?? "").trim();
  const q = (searchParams.get("q") ?? "").trim();
  const asOfDate = (searchParams.get("asOfDate") ?? "").trim();

  if (!custCode) {
    return NextResponse.json({ suggestions: [] as string[] });
  }
  if (q.length < 3) {
    return NextResponse.json({ suggestions: [] as string[] });
  }
  if (q.length > 40) {
    return NextResponse.json({ suggestions: [] as string[] });
  }
  if (!GONEN_AS_OF_DATE_REGEX.test(asOfDate)) {
    return NextResponse.json({ error: "対象日付は yyyy/mm/dd で指定してください" }, { status: 400 });
  }

  try {
    const suggestions = await listGonenKukumiCustItemSuggestions({
      custCode,
      prefix: q,
      asOfDate,
    });
    return NextResponse.json({ suggestions });
  } catch (e) {
    return jsonErrorResponse(e, { suggestions: [] as string[] });
  }
}
