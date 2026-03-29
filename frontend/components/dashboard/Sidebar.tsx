"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Search,
  Users,
  KeyRound,
  FileText,
  Eye,
  Bot,
  Settings,
  LogOut,
} from "lucide-react";
import { auth } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Overview" },
];

const PROJECT_NAV = [
  { href: "/keywords", icon: KeyRound, label: "Keywords" },
  { href: "/competitors", icon: Users, label: "Competitors" },
  { href: "/changes", icon: FileText, label: "Changes" },
  { href: "/geo", icon: Eye, label: "AI Visibility" },
];

export default function Sidebar({ projectId }: { projectId?: string }) {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[240px] bg-surface-50 border-r border-zinc-800/60 flex flex-col z-40">
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-zinc-800/60">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white text-sm font-bold">
            S
          </div>
          <span className="font-display text-lg text-zinc-100">
            SEO<span className="text-brand-400">Tracker</span>
          </span>
        </Link>
      </div>

      {/* Main nav */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <p className="text-[10px] uppercase tracking-[0.15em] text-zinc-600 font-semibold px-2 mb-2">
          General
        </p>
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all",
                active
                  ? "bg-brand-600/15 text-brand-300 font-medium"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              )}
            >
              <item.icon size={16} />
              {item.label}
            </Link>
          );
        })}

        {projectId && (
          <>
            <p className="text-[10px] uppercase tracking-[0.15em] text-zinc-600 font-semibold px-2 mt-6 mb-2">
              Project
            </p>
            {PROJECT_NAV.map((item) => {
              const href = `/dashboard/${projectId}${item.href}`;
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all",
                    active
                      ? "bg-brand-600/15 text-brand-300 font-medium"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
                  )}
                >
                  <item.icon size={16} />
                  {item.label}
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* Bottom */}
      <div className="p-3 border-t border-zinc-800/60 space-y-1">
        <button
          onClick={() => auth.logout()}
          className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-500 hover:text-red-400 hover:bg-red-500/5 transition-all w-full"
        >
          <LogOut size={16} />
          Log out
        </button>
      </div>
    </aside>
  );
}
