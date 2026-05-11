"use client";

import { signIn } from "next-auth/react";
import { useTransition } from "react";

type LoginClientFormsProps = {
  callbackUrl: string;
  showMicrosoft: boolean;
  showDev: boolean;
};

export function LoginClientForms({
  callbackUrl,
  showMicrosoft,
  showDev,
}: LoginClientFormsProps) {
  return (
    <>
      {showMicrosoft && (
        <MicrosoftSignInForm callbackUrl={callbackUrl} />
      )}
      {showDev && <DevSignInForm callbackUrl={callbackUrl} />}
    </>
  );
}

function MicrosoftSignInForm({ callbackUrl }: { callbackUrl: string }) {
  const [pending, startTransition] = useTransition();

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    startTransition(() => {
      void signIn(
        "microsoft-entra-id",
        { redirectTo: callbackUrl },
        { prompt: "login" },
      );
    });
  }

  return (
    <form onSubmit={onSubmit}>
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-lg bg-[#0078d4] px-4 py-3 text-sm font-medium text-white transition hover:bg-[#106ebe] disabled:opacity-60"
      >
        Microsoft で続行
      </button>
    </form>
  );
}

function DevSignInForm({ callbackUrl }: { callbackUrl: string }) {
  const [pending, startTransition] = useTransition();

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const password = String(new FormData(form).get("password") ?? "");

    startTransition(() => {
      void (async () => {
        const res = await signIn("dev-local", {
          email: "dev@local",
          password,
          redirect: false,
          redirectTo: callbackUrl,
        });
        if (res?.error) {
          window.location.href = `/login?error=credentials&callbackUrl=${encodeURIComponent(callbackUrl)}`;
          return;
        }
        if (res?.url) {
          window.location.href = res.url;
        }
      })();
    });
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mt-4 space-y-3 border-t border-slate-200 pt-4"
    >
      <p className="text-xs font-medium text-slate-600">
        開発用ログイン（AUTH_DEV_MODE）
      </p>
      <input
        type="password"
        name="password"
        placeholder="パスワード: dev"
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        autoComplete="current-password"
        disabled={pending}
      />
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-lg border border-slate-300 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100 disabled:opacity-60"
      >
        開発ユーザーで入る
      </button>
    </form>
  );
}
