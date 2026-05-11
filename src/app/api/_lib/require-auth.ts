import { NextResponse } from "next/server";
import { auth } from "@/auth";

/**
 * API ルートの「認証必須」ガード。すべての `/api/**` で同じ
 * 「`auth()` → セッション無ければ 401」処理が散らばらないように集約する。
 */
export async function requireAuthenticatedUser(): Promise<
  | { ok: true; userId: string }
  | { ok: false; response: NextResponse }
> {
  const session = await auth();
  const userId = session?.user?.id;
  if (!userId) {
    return {
      ok: false,
      response: NextResponse.json({ error: "認証が必要です" }, { status: 401 }),
    };
  }
  return { ok: true, userId };
}

/**
 * 例外をそのまま 500 JSON 応答に変換する共通ヘルパー。
 * 一覧系 API では `items: []` のような既定フィールドを併せて返したいので
 * `extra` でマージできるようにする。
 */
export function jsonErrorResponse(e: unknown, extra?: Record<string, unknown>): NextResponse {
  const msg = e instanceof Error ? e.message : String(e);
  return NextResponse.json({ error: msg, ...(extra ?? {}) }, { status: 500 });
}
