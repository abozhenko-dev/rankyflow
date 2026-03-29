import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPosition(pos: number | null): string {
  if (pos === null || pos === undefined) return "100+";
  return `#${pos}`;
}

export function formatChange(change: number | null): string {
  if (change === null || change === undefined) return "—";
  if (change > 0) return `+${change}`;
  return `${change}`;
}

export function formatPercent(val: number): string {
  return `${(val * 100).toFixed(1)}%`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "major":
    case "critical":
    case "high":
      return "text-red-400";
    case "moderate":
    case "medium":
      return "text-amber-400";
    case "minor":
    case "low":
      return "text-emerald-400";
    default:
      return "text-zinc-400";
  }
}

export function platformIcon(platform: string): string {
  switch (platform) {
    case "chatgpt":  return "🤖";
    case "perplexity": return "🔍";
    case "claude":   return "🧠";
    case "gemini":   return "✨";
    case "deepseek": return "🌊";
    default:         return "💬";
  }
}
