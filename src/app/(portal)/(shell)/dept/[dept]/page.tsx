import { PortalPlaceholderPage } from "@/components/portal-placeholder-page";

const labels: Record<string, string> = {
  "company-wide": "全社",
  hr: "人事",
  "general-affairs": "総務",
  finance: "財務",
  sales: "営業",
  production: "生産管理",
  quality: "品保",
};

export default async function DeptPage({
  params,
}: {
  params: Promise<{ dept: string }>;
}) {
  const { dept } = await params;
  const title = labels[dept] ?? dept;

  return (
    <PortalPlaceholderPage
      title={title}
      description="この部門向けのアプリは順次追加予定です。"
    />
  );
}
