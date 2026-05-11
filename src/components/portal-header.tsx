import { SignOutButton } from "@/components/sign-out-button";

export function PortalHeader({ userName }: { userName?: string | null }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
      <span className="text-sm text-slate-600">
        {userName ? `ようこそ、${userName} さん` : ""}
      </span>
      <SignOutButton />
    </header>
  );
}
