import { PortalPlaceholderPage } from "@/components/portal-placeholder-page";

const titles: Record<string, string> = {
  "five-year-nine": "5年9組",
  "inspection-compare": "検収書比較",
  "indication-order": "内示受注変換",
  "firmed-order": "確定受注変換",
};

export default async function ProductionAppPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const title = titles[slug] ?? slug;

  return (
    <PortalPlaceholderPage
      title={title}
      description="画面・API は今後の要件に応じて実装します（仕様書 3.2）。"
    />
  );
}
