"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { data as dataApi } from "@/lib/api";
import { cn, severityColor, formatDate } from "@/lib/utils";
import { Loader2, FileText, RefreshCw, AlertTriangle, ChevronDown, ChevronRight } from "lucide-react";

// Type matching backend ChangeResponse
interface ChangeEntry {
  id: string;
  competitor_name: string;
  competitor_domain: string;
  page_url: string;
  severity: "minor" | "moderate" | "major";
  change_type: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  ai_summary: string | null;
  detected_at: string;
}

export default function ChangesPage() {
  const { projectId } = useParams() as { projectId: string };
  const [changes, setChanges] = useState<ChangeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "major" | "moderate" | "minor">("all");

  useEffect(() => {
    loadChanges();
  }, [projectId, filter]);

  async function loadChanges() {
    setLoading(true);
    try {
      const data = await changesApi.list(projectId, {
        severity: filter === "all" ? undefined : filter,
        days: 30,
        limit: 100,
      });
      setChanges(data);
    } catch (e) {
      // Fallback to empty — real data appears after first crawler run
      setChanges([]);
    } finally {
      setLoading(false);
    }
  }

  const filtered = changes;

  const severityIcon = (s: string) => {
    switch (s) {
      case "major": return <AlertTriangle size={14} className="text-red-400" />;
      case "moderate": return <RefreshCw size={14} className="text-amber-400" />;
      default: return <FileText size={14} className="text-zinc-500" />;
    }
  };

  const severityBadge = (s: string) => {
    const colors: Record<string, string> = {
      major: "bg-red-500/10 text-red-400 border-red-500/20",
      moderate: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      minor: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    };
    return colors[s] || colors.minor;
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl text-zinc-100">Change Log</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Competitor website changes detected by crawler
          </p>
        </div>
      </div>

      {/* Filter pills */}
      <div className="flex items-center gap-2 mb-6">
        {(["all", "major", "moderate", "minor"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              "px-3 py-1.5 text-xs rounded-lg border transition",
              filter === f
                ? "bg-brand-600/15 text-brand-300 border-brand-600/30"
                : "bg-surface-200 text-zinc-500 border-zinc-800 hover:text-zinc-300"
            )}
          >
            {f === "all" ? `All (${changes.length})` : `${f} (${changes.filter(c => c.severity === f).length})`}
          </button>
        ))}
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 size={24} className="animate-spin text-zinc-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-zinc-800 rounded-2xl">
          <FileText size={40} className="mx-auto text-zinc-700 mb-4" />
          <p className="text-zinc-400">No changes detected yet</p>
          <p className="text-xs text-zinc-600 mt-1">
            Changes will appear here after the daily crawler runs
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((change) => {
            const expanded = expandedId === change.id;
            return (
              <div
                key={change.id}
                className="bg-surface-100 border border-zinc-800/60 rounded-xl overflow-hidden hover:border-zinc-700/60 transition"
              >
                <button
                  className="w-full px-5 py-4 flex items-start gap-4 text-left"
                  onClick={() => setExpandedId(expanded ? null : change.id)}
                >
                  <div className="mt-0.5">{severityIcon(change.severity)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-zinc-200">
                        {change.competitor_name}
                      </span>
                      <span className={cn(
                        "text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border",
                        severityBadge(change.severity)
                      )}>
                        {change.severity}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-200 text-zinc-500">
                        {change.field_name}
                      </span>
                    </div>
                    {change.ai_summary ? (
                      <p className="text-sm text-zinc-400 line-clamp-2">
                        {change.ai_summary}
                      </p>
                    ) : (
                      <p className="text-xs text-zinc-500 font-mono truncate">
                        {change.page_url}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-zinc-600">
                      {formatDate(change.detected_at)}
                    </span>
                    {expanded ? (
                      <ChevronDown size={14} className="text-zinc-500" />
                    ) : (
                      <ChevronRight size={14} className="text-zinc-500" />
                    )}
                  </div>
                </button>

                {/* Expanded detail */}
                {expanded && (
                  <div className="px-5 pb-5 border-t border-zinc-800/40 pt-4 ml-[44px]">
                    <div className="text-xs text-zinc-500 font-mono mb-3">
                      {change.page_url}
                    </div>
                    {change.old_value && (
                      <div className="mb-2">
                        <span className="text-[10px] uppercase tracking-wider text-zinc-600">
                          Before:
                        </span>
                        <div className="mt-1 px-3 py-2 bg-red-500/5 border border-red-500/10 rounded-lg text-sm text-red-300/70 font-mono">
                          {change.old_value}
                        </div>
                      </div>
                    )}
                    {change.new_value && (
                      <div className="mb-2">
                        <span className="text-[10px] uppercase tracking-wider text-zinc-600">
                          After:
                        </span>
                        <div className="mt-1 px-3 py-2 bg-emerald-500/5 border border-emerald-500/10 rounded-lg text-sm text-emerald-300/70 font-mono">
                          {change.new_value}
                        </div>
                      </div>
                    )}
                    {change.ai_summary && (
                      <div className="mt-3 px-3 py-2 bg-brand-600/5 border border-brand-600/10 rounded-lg">
                        <span className="text-[10px] uppercase tracking-wider text-brand-400">
                          🧠 AI Analysis
                        </span>
                        <p className="text-sm text-zinc-300 mt-1">
                          {change.ai_summary}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
