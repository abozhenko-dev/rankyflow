"use client";

import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: LucideIcon;
  className?: string;
}

export default function StatCard({
  label,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "bg-surface-100 border border-zinc-800/60 rounded-xl p-5 transition-colors hover:border-zinc-700/60",
        className
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs uppercase tracking-[0.1em] text-zinc-500 font-medium">
          {label}
        </span>
        {Icon && (
          <div className="w-8 h-8 rounded-lg bg-surface-200 flex items-center justify-center">
            <Icon size={14} className="text-zinc-400" />
          </div>
        )}
      </div>
      <div className="text-2xl font-semibold text-zinc-100 tracking-tight">
        {value}
      </div>
      {change && (
        <span
          className={cn(
            "text-xs font-mono mt-1 inline-block",
            changeType === "positive" && "text-emerald-400",
            changeType === "negative" && "text-red-400",
            changeType === "neutral" && "text-zinc-500"
          )}
        >
          {change}
        </span>
      )}
    </div>
  );
}
