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
    <div>
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 text-sm text-slate-600">
        画面・API は今後の要件に応じて実装します（仕様書 3.2）。
      </p>
    </div>
  );
}
