import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { GONEN_AS_OF_DATE_REGEX } from "@/domains/gonenkukumi/schemas";
import { listGonenKukumiCustItems } from "@/infrastructure/oracle/gonenkukumi/list-cust-items";

/** 得意先品目のプリフェッチ用（全件）。GET ?custCode=&asOfDate= */
export async function GET(req: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
  }

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
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg, items: [] as string[] }, { status: 500 });
  }
}

