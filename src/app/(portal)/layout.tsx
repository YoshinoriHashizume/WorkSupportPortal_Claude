import { requirePageSession } from "@/app/_lib/server-auth";

export default async function PortalLayout({ children }: { children: React.ReactNode }) {
  await requirePageSession();
  return children;
}
