import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { GONEN_AS_OF_DATE_REGEX } from "@/domains/gonenkukumi/schemas";
import { listGonenKukumiCustItemSuggestions } from "@/infrastructure/oracle/gonenkukumi/list-cust-item-suggestions";

/** 得意先品目のオートコンプリート用。GET ?custCode=&q=&asOfDate= （q は 3 文字以上） */
export async function GET(req: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
  }

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
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg, suggestions: [] as string[] }, { status: 500 });
  }
}
