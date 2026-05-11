import type { PrismaClient } from "@prisma/client";

export type MenuTreeNode = {
  id: string;
  label: string;
  href: string;
  sortOrder: number;
  departmentKey: string;
  children: MenuTreeNode[];
};

/**
 * ユーザーが参照可能なメニューのみを木構造で返す（PostgreSQL 正）。
 */
export async function getMenuTreeForUser(
  db: PrismaClient,
  userId: string,
): Promise<MenuTreeNode[]> {
  const allowed = await db.userMenuAccess.findMany({
    where: { userId },
    select: { menuItemId: true },
  });
  const allowedSet = new Set(allowed.map((a) => a.menuItemId));

  const items = await db.menuItem.findMany({
    orderBy: [{ sortOrder: "asc" }, { label: "asc" }],
  });

  const nodes = new Map<string, MenuTreeNode>();
  for (const it of items) {
    if (!allowedSet.has(it.id)) continue;
    nodes.set(it.id, {
      id: it.id,
      label: it.label,
      href: it.href,
      sortOrder: it.sortOrder,
      departmentKey: it.departmentKey,
      children: [],
    });
  }

  const roots: MenuTreeNode[] = [];
  for (const it of items) {
    if (!allowedSet.has(it.id)) continue;
    const node = nodes.get(it.id)!;
    if (it.parentId && nodes.has(it.parentId)) {
      nodes.get(it.parentId)!.children.push(node);
    } else if (!it.parentId) {
      roots.push(node);
    }
  }

  const sortChildren = (n: MenuTreeNode) => {
    n.children.sort((a, b) => a.sortOrder - b.sortOrder || a.label.localeCompare(b.label));
    n.children.forEach(sortChildren);
  };
  roots.sort((a, b) => a.sortOrder - b.sortOrder);
  roots.forEach(sortChildren);
  return roots;
}
