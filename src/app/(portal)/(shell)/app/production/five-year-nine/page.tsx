import { requirePageSession } from "@/app/_lib/server-auth";
import { prisma } from "@/infrastructure/persistence/prisma/client";
import { GonenKukumiSearchClient, type HistoryRow } from "./search-client";

export default async function GonenKukumiSearchPage() {
  const { userId } = await requirePageSession();

  const rows = await prisma.gonenKukumiSearchHistory.findMany({
    where: { userId },
    orderBy: { executedAt: "desc" },
    distinct: ["custCode", "custItem", "optionChange", "yearMonth"],
    take: 20,
  });

  const initialHistory: HistoryRow[] = rows.map((r) => ({
    id: r.id,
    executedAt: r.executedAt.toISOString(),
    custCode: r.custCode,
    custItem: r.custItem,
    optionChange: r.optionChange,
    yearMonth: r.yearMonth,
  }));

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">5年9組</h1>
      <div className="mt-6">
        <GonenKukumiSearchClient initialHistory={initialHistory} />
      </div>
    </div>
  );
}
