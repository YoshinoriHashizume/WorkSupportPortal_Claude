import { redirectIfAuthenticated } from "@/app/_lib/server-auth";
import { LoginClientForms } from "./login-client-forms";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string; error?: string }>;
}) {
  const params = await searchParams;
  await redirectIfAuthenticated(params.callbackUrl ?? "/dashboard");

  const devMode =
    process.env.NODE_ENV === "development" &&
    process.env.AUTH_DEV_MODE === "true";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-center text-xl font-semibold text-slate-900">
          Core Data Integration Portal
        </h1>
        <p className="mt-1 text-center text-sm text-slate-500">
          基幹データ連携ポータル
        </p>

        <div className="mt-8 flex flex-col gap-3">
          {!process.env.AUTH_MICROSOFT_ENTRA_ID_ID && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-center text-xs text-amber-900">
              Entra ID の環境変数（AUTH_MICROSOFT_ENTRA_ID_*）が未設定です。
              `.env.local` を参照してください。
            </p>
          )}

          <LoginClientForms
            callbackUrl={params.callbackUrl ?? "/dashboard"}
            showMicrosoft={Boolean(process.env.AUTH_MICROSOFT_ENTRA_ID_ID)}
            showDev={devMode}
          />
        </div>

        {params.error && (
          <p className="mt-4 text-center text-sm text-red-600">
            {params.error === "credentials"
              ? "メールまたはパスワードが正しくありません（開発は dev@local / dev）。"
              : `認証エラー: ${params.error}`}
          </p>
        )}
      </div>
    </div>
  );
}
