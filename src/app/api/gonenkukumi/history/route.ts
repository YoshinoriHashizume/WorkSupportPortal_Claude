import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/infrastructure/persistence/prisma/client";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
  }

  const rows = await prisma.gonenKukumiSearchHistory.findMany({
    where: { userId: session.user.id },
    orderBy: { executedAt: "desc" },
    distinct: ["custCode", "custItem", "optionChange", "yearMonth"],
    take: 50,
    select: {
      id: true,
      executedAt: true,
      custCode: true,
      custItem: true,
      optionChange: true,
      yearMonth: true,
    },
  });

  return NextResponse.json({ items: rows });
}
