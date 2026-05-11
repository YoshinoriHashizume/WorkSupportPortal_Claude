import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { prisma } from "@/infrastructure/persistence/prisma/client";
import { getMenuTreeForUser } from "@/domains/identity/application/get-menu-for-user";
import { PortalSidebar } from "@/components/portal-sidebar";
import { PortalHeader } from "@/components/portal-header";

export default async function PortalShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/login");
  }

  const tree = await getMenuTreeForUser(prisma, session.user.id);

  return (
    <div className="flex min-h-screen">
      <PortalSidebar tree={tree} />
      <div className="flex min-h-screen flex-1 flex-col">
        <PortalHeader userName={session.user.name} />
        <main className="flex-1 bg-slate-50 p-6">{children}</main>
      </div>
    </div>
  );
}
