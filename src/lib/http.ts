/**
 * クライアント側 fetch ラッパー。
 *
 * `fetch → res.text → JSON.parse → 空応答 / 非 JSON / HTTP エラー / ネットワーク例外`
 * の場合分けが各コンポーネントで重複していたため共通化する。
 *
 * - 成功時: `{ ok: true; status, data }`
 * - 失敗時: `{ ok: false; status, error, body? }`
 *
 * 想定されない応答形式（HTML レスポンス等）はメッセージ付きで失敗扱いに揃える。
 */

export type JsonResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: string; body?: unknown };

function extractApiErrorMessage(body: unknown, fallback: string): string {
  if (typeof body === "object" && body && "error" in body) {
    const v = (body as { error: unknown }).error;
    if (typeof v === "string" && v.trim() !== "") return v;
  }
  return fallback;
}

async function parseJsonBody<T>(res: Response): Promise<JsonResult<T>> {
  const raw = await res.text();
  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    return {
      ok: false,
      status: res.status,
      error: res.ok
        ? "サーバーから空の応答が返りました（JSON がありません）。API またはプロキシの設定を確認してください。"
        : `サーバーエラー (${res.status})。応答ボディが空です。`,
    };
  }
  let body: unknown;
  try {
    body = JSON.parse(trimmed);
  } catch {
    return {
      ok: false,
      status: res.status,
      error: res.ok
        ? "サーバーからの応答を解釈できませんでした（有効な JSON ではありません）。"
        : `サーバーエラー (${res.status})。応答が HTML の場合は API 側で例外が出ている可能性があります。`,
    };
  }
  if (!res.ok) {
    return {
      ok: false,
      status: res.status,
      error: extractApiErrorMessage(body, `エラー (${res.status})`),
      body,
    };
  }
  return { ok: true, status: res.status, data: body as T };
}

export async function getJson<T>(
  url: string,
  init?: { signal?: AbortSignal; credentials?: RequestCredentials },
): Promise<JsonResult<T>> {
  try {
    const res = await fetch(url, {
      method: "GET",
      signal: init?.signal,
      credentials: init?.credentials,
    });
    return await parseJsonBody<T>(res);
  } catch (e) {
    if ((e as Error).name === "AbortError") {
      return { ok: false, status: 0, error: "aborted" };
    }
    return {
      ok: false,
      status: 0,
      error: e instanceof Error ? e.message : "通信中にエラーが発生しました。",
    };
  }
}

export async function postJson<T>(
  url: string,
  body: unknown,
  init?: { signal?: AbortSignal; credentials?: RequestCredentials },
): Promise<JsonResult<T>> {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: init?.signal,
      credentials: init?.credentials,
    });
    return await parseJsonBody<T>(res);
  } catch (e) {
    if ((e as Error).name === "AbortError") {
      return { ok: false, status: 0, error: "aborted" };
    }
    return {
      ok: false,
      status: 0,
      error: e instanceof Error ? e.message : "通信中にエラーが発生しました。",
    };
  }
}
