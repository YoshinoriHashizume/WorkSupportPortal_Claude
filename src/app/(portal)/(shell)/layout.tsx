import { requirePageSession } from "@/app/_lib/server-auth";
import { prisma } from "@/infrastructure/persistence/prisma/client";
import { getMenuTreeForUser } from "@/domains/identity/application/get-menu-for-user";
import { PortalSidebar } from "@/components/portal-sidebar";
import { PortalHeader } from "@/components/portal-header";

export default async function PortalShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userId, userName } = await requirePageSession();
  const tree = await getMenuTreeForUser(prisma, userId);

  return (
    <div className="flex min-h-screen">
      <PortalSidebar tree={tree} />
      <div className="flex min-h-screen flex-1 flex-col">
        <PortalHeader userName={userName} />
        <main className="flex-1 bg-slate-50 p-6">{children}</main>
      </div>
    </div>
  );
}
