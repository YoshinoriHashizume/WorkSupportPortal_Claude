import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

/**
 * 仕様書 7.2 / 7.3 に基づくメニュー木のシード。
 * 第1階層: 全社〜品保、生産管理配下に子リンク。
 */
async function main() {
  const departments: { key: string; label: string; sort: number }[] = [
    { key: "company-wide", label: "全社", sort: 1 },
    { key: "hr", label: "人事", sort: 2 },
    { key: "general-affairs", label: "総務", sort: 3 },
    { key: "finance", label: "財務", sort: 4 },
    { key: "sales", label: "営業", sort: 5 },
    { key: "production", label: "生産管理", sort: 6 },
    { key: "quality", label: "品保", sort: 7 },
  ];

  for (const d of departments) {
    const existing = await prisma.menuItem.findFirst({
      where: { parentId: null, departmentKey: d.key, label: d.label },
    });
    if (existing) continue;

    await prisma.menuItem.create({
      data: {
        parentId: null,
        label: d.label,
        href: `/dept/${d.key}`,
        sortOrder: d.sort,
        departmentKey: d.key,
      },
    });
  }

  const production = await prisma.menuItem.findFirst({
    where: { departmentKey: "production", parentId: null, label: "生産管理" },
  });

  if (production) {
    const children: { label: string; href: string; sort: number }[] = [
      { label: "5年9組", href: "/app/production/five-year-nine", sort: 1 },
      { label: "検収書比較", href: "/app/production/inspection-compare", sort: 2 },
      { label: "内示受注変換", href: "/app/production/indication-order", sort: 3 },
      { label: "確定受注変換", href: "/app/production/firmed-order", sort: 4 },
    ];

    for (const c of children) {
      const exists = await prisma.menuItem.findFirst({
        where: { parentId: production.id, label: c.label },
      });
      if (exists) continue;
      await prisma.menuItem.create({
        data: {
          parentId: production.id,
          label: c.label,
          href: c.href,
          sortOrder: c.sort,
          departmentKey: "production",
        },
      });
    }
  }

  console.log("Menu seed completed.");
}

main()
  .then(() => prisma.$disconnect())
  .catch((e) => {
    console.error(e);
    prisma.$disconnect();
    process.exit(1);
  });
