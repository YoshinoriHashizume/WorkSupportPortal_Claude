import { NextResponse } from "next/server";
import { requireAuthenticatedUser } from "@/app/api/_lib/require-auth";
import { listGonenKukumiCustomers } from "@/infrastructure/oracle/gonenkukumi/list-customers";

export async function GET() {
  const guard = await requireAuthenticatedUser();
  if (!guard.ok) return guard.response;

  try {
    const items = await listGonenKukumiCustomers();
    return NextResponse.json({ items });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ items: [], loadError: msg }, { status: 200 });
  }
}
