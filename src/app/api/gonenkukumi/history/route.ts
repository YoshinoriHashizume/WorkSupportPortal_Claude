import { NextResponse } from "next/server";
import { requireAuthenticatedUser } from "@/app/api/_lib/require-auth";
import { prisma } from "@/infrastructure/persistence/prisma/client";

export async function GET() {
  const guard = await requireAuthenticatedUser();
  if (!guard.ok) return guard.response;

  const rows = await prisma.gonenKukumiSearchHistory.findMany({
    where: { userId: guard.userId },
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
