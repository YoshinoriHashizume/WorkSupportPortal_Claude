import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { listGonenKukumiCustomers } from "@/infrastructure/oracle/gonenkukumi/list-customers";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
  }

  try {
    const items = await listGonenKukumiCustomers();
    return NextResponse.json({ items });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ items: [], loadError: msg }, { status: 200 });
  }
}
