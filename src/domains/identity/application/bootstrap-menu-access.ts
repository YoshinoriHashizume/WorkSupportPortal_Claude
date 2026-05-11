import type { PrismaClient } from "@prisma/client";

/**
 * 初回ログイン時にメニュー権限が空なら、全 MenuItem を付与する（MVP）。
 * 本番運用では管理者による付与に差し替える想定（仕様書 6.3）。
 */
export async function ensureUserHasMenuAccess(
  db: PrismaClient,
  userId: string,
): Promise<void> {
  const count = await db.userMenuAccess.count({ where: { userId } });
  if (count > 0) return;

  const items = await db.menuItem.findMany({ select: { id: true } });
  if (items.length === 0) return;

  await db.userMenuAccess.createMany({
    data: items.map((i) => ({ userId, menuItemId: i.id })),
    skipDuplicates: true,
  });
}
