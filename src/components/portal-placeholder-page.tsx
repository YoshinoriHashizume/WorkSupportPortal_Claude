/**
 * 「タイトル + 説明文だけ」の暫定ページ用プレースホルダー。
 * dashboard / 部門ページ / アプリ未実装ページの 3 箇所で共有する。
 */
export function PortalPlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div>
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
    </div>
  );
}
