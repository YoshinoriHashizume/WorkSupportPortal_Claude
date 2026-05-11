import { NextResponse } from "next/server";
import { requireAuthenticatedUser } from "@/app/api/_lib/require-auth";
import { gonenKukumiSearchSchema } from "@/domains/gonenkukumi/schemas";
import type { GonenKukumiSearchInput } from "@/domains/gonenkukumi/schemas";
import type { GonenKukumiOracleFailure } from "@/domains/gonenkukumi/types";

export async function parseGonenKukumiAuthenticatedSearchPost(req: Request): Promise<
  | { ok: true; userId: string; input: GonenKukumiSearchInput }
  | { ok: false; response: NextResponse }
> {
  const guard = await requireAuthenticatedUser();
  if (!guard.ok) return guard;

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return { ok: false, response: NextResponse.json({ error: "JSON が不正です" }, { status: 400 }) };
  }

  const parsed = gonenKukumiSearchSchema.safeParse(body);
  if (!parsed.success) {
    return {
      ok: false,
      response: NextResponse.json(
        { error: "入力エラー", details: parsed.error.flatten() },
        { status: 400 },
      ),
    };
  }

  return { ok: true, userId: guard.userId, input: parsed.data };
}

export function gonenOracleFailureResponse(oracle: GonenKukumiOracleFailure): NextResponse {
  const status =
    oracle.code === "ORACLE_NOT_CONFIGURED"
      ? 503
      : oracle.code === "NAISAK_NOT_FOUND"
        ? 404
        : 502;
  return NextResponse.json({ error: oracle.message, code: oracle.code }, { status });
}
