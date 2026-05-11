"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { MenuTreeNode } from "@/domains/identity/application/get-menu-for-user";

type Props = {
  tree: MenuTreeNode[];
};

const STORAGE_KEY = "portal-sidebar-collapsed";

function IconChevronLeft({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function IconChevronRight({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

export function PortalSidebar({ tree }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      if (v === "1") setCollapsed(true);
    } catch {
      /* ignore */
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [collapsed, hydrated]);

  return (
    <div className="relative shrink-0">
      <aside
        className={`overflow-hidden border-slate-800 bg-slate-900 text-slate-100 transition-[width] duration-300 ease-in-out motion-reduce:transition-none ${
          collapsed ? "w-0 border-r-0" : "w-64 border-r"
        }`}
        aria-hidden={collapsed}
      >
        <div className="flex min-h-screen w-64 flex-col">
          <div className="flex items-start justify-between gap-2 border-b border-slate-700 px-3 py-4">
            <div className="min-w-0 flex-1">
              <Link href="/dashboard" className="font-semibold tracking-tight">
                Core Data Integration Portal
              </Link>
              <p className="mt-0.5 text-xs text-slate-400">メニュー</p>
            </div>
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              className="shrink-0 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
              aria-label="メニューを閉じる"
              title="メニューを閉じる"
            >
              <IconChevronLeft className="block" />
            </button>
          </div>
          <nav className="flex-1 overflow-y-auto px-2 py-3 text-sm">
            <ul className="space-y-1">
              {tree.map((node) => (
                <li key={node.id}>
                  <NavBranch node={node} depth={0} />
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </aside>

      {collapsed && (
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="fixed left-0 top-6 z-40 flex h-11 w-9 items-center justify-center rounded-r-md border border-l-0 border-slate-700 bg-slate-900 text-slate-200 shadow-md transition-colors hover:bg-slate-800"
          aria-label="メニューを開く"
          title="メニューを開く"
        >
          <IconChevronRight className="block" />
        </button>
      )}
    </div>
  );
}

function NavBranch({ node, depth }: { node: MenuTreeNode; depth: number }) {
  const hasChildren = node.children.length > 0;
  return (
    <div className={depth > 0 ? "ml-2 border-l border-slate-700 pl-2" : ""}>
      <Link
        href={node.href}
        className="block rounded-md px-2 py-1.5 text-slate-200 hover:bg-slate-800 hover:text-white"
      >
        {node.label}
      </Link>
      {hasChildren && (
        <ul className="mt-1 space-y-0.5">
          {node.children.map((ch) => (
            <li key={ch.id}>
              <NavBranch node={ch} depth={depth + 1} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
