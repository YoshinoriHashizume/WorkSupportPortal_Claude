"use client";

import { signOut } from "next-auth/react";
import { useTransition } from "react";

export function SignOutButton() {
  const [pending, startTransition] = useTransition();

  function onClick() {
    startTransition(() => {
      void signOut({ redirectTo: "/login" });
    });
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
    >
      ログアウト
    </button>
  );
}
