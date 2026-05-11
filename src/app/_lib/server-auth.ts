import "server-only";

import { redirect } from "next/navigation";
import { auth } from "@/auth";

/**
 * 認証必須ページ／レイアウト向けの共通ガード。
 * セッション or `user.id` が無ければ `/login` に redirect する。
 *
 * 各 page / layout で `const session = await auth(); if (!session?.user?.id) redirect("/login")`
 * と書いていた箇所を 1 行に置き換える。
 */
export async function requirePageSession(): Promise<{
  userId: string;
  userName: string | null | undefined;
}> {
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/login");
  }
  return { userId: session.user.id, userName: session.user.name };
}

/**
 * 認証不要ページ（例: `/login`、`/`）でセッションがあるときだけ別 URL へ飛ばす。
 * `/login?callbackUrl=...` のような遷移先制御に対応する。
 */
export async function redirectIfAuthenticated(toIfAuthenticated: string): Promise<void> {
  const session = await auth();
  if (session?.user) {
    redirect(toIfAuthenticated);
  }
}
