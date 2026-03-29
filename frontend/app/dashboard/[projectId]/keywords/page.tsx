"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { keywords as kwApi, agents } from "@/lib/api";
import type { Keyword } from "@/types";
import { formatPosition, formatChange, cn } from "@/lib/utils";
import {
  Plus,
  Upload,
  Trash2,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  Play,
  ArrowUpDown,
  BarChart3,
} from "lucide-react";
import RankChart from "@/components/charts/RankChart";

export default function KeywordsPage() {
  const { projectId } = useParams() as { projectId: string };
  const [kws, setKws] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newKw, setNewKw] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [bulkMode, setBulkMode] = useState(false);
  const [adding, setAdding] = useState(false);
  const [sortField, setSortField] = useState<"keyword" | "position" | "change">("keyword");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    loadKeywords();
  }, [projectId]);

  async function loadKeywords() {
    try {
      const data = await kwApi.list(projectId);
      setKws(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    setAdding(true);
    try {
      if (bulkMode) {
        const lines = bulkText
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean);
        if (lines.length) {
          await kwApi.bulkAdd(projectId, lines);
        }
        setBulkText("");
      } else {
        if (newKw.trim()) {
          await kwApi.add(projectId, newKw.trim());
        }
        setNewKw("");
      }
      setShowAdd(false);
      loadKeywords();
    } catch (e) {
      console.error(e);
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await kwApi.remove(id);
      setKws((prev) => prev.filter((k) => k.id !== id));
    } catch (e) {
      console.error(e);
    }
  }

  async function handleRunTracker() {
    try {
      await agents.runSingle(projectId, "rank_tracker");
    } catch (e) {
      console.error(e);
    }
  }

  // Sorting
  const sorted = [...kws].sort((a, b) => {
    let cmp = 0;
    if (sortField === "keyword") cmp = a.keyword.localeCompare(b.keyword);
    else if (sortField === "position")
      cmp = (a.latest_position ?? 999) - (b.latest_position ?? 999);
    else if (sortField === "change")
      cmp = (a.position_change ?? 0) - (b.position_change ?? 0);
    return sortDir === "asc" ? cmp : -cmp;
  });

  function toggleSort(field: typeof sortField) {
    if (sortField === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  const improved = kws.filter((k) => k.position_change && k.position_change > 0).length;
  const declined = kws.filter((k) => k.position_change && k.position_change < 0).length;

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl text-zinc-100">Keywords</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            {kws.length} tracked ·{" "}
            <span className="text-emerald-400">{improved} up</span> ·{" "}
            <span className="text-red-400">{declined} down</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRunTracker}
            className="flex items-center gap-1.5 px-3 py-2 text-xs bg-surface-200 hover:bg-surface-300 text-zinc-300 rounded-lg transition"
          >
            <Play size={12} />
            Run check
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg transition"
          >
            <Plus size={14} />
            Add
          </button>
        </div>
      </div>

      {/* Add modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-surface-100 border border-zinc-800 rounded-2xl p-6 w-full max-w-lg animate-slide-up">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-xl">Add Keywords</h2>
              <div className="flex gap-1 bg-surface-200 rounded-lg p-0.5">
                <button
                  onClick={() => setBulkMode(false)}
                  className={cn(
                    "px-3 py-1 text-xs rounded-md transition",
                    !bulkMode ? "bg-brand-600 text-white" : "text-zinc-400"
                  )}
                >
                  Single
                </button>
                <button
                  onClick={() => setBulkMode(true)}
                  className={cn(
                    "px-3 py-1 text-xs rounded-md transition",
                    bulkMode ? "bg-brand-600 text-white" : "text-zinc-400"
                  )}
                >
                  <Upload size={12} className="inline mr-1" />
                  Bulk
                </button>
              </div>
            </div>

            {bulkMode ? (
              <textarea
                placeholder="One keyword per line..."
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                rows={8}
                className="w-full px-4 py-3 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
              />
            ) : (
              <input
                type="text"
                placeholder="Enter keyword..."
                value={newKw}
                onChange={(e) => setNewKw(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                className="w-full px-4 py-2.5 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            )}

            <div className="flex justify-end gap-3 mt-5">
              <button
                onClick={() => setShowAdd(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={adding}
                className="px-5 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
              >
                {adding && <Loader2 size={14} className="animate-spin" />}
                {bulkMode ? "Import" : "Add"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rank History Chart — demo data, will be replaced by real API */}
      {kws.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 size={14} className="text-zinc-500" />
            <span className="text-xs uppercase tracking-[0.1em] text-zinc-500 font-semibold">
              Position History (last 14 days)
            </span>
          </div>
          <RankChart
            data={generateDemoRankData(kws.slice(0, 1).map(k => k.keyword))}
            domains={["your-site.com", "competitor-1.com", "competitor-2.com"]}
            ownDomain="your-site.com"
          />
        </div>
      )}

      {/* Keywords table */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 size={24} className="animate-spin text-zinc-500" />
        </div>
      ) : kws.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-zinc-800 rounded-2xl">
          <p className="text-zinc-400 mb-2">No keywords tracked yet</p>
          <button
            onClick={() => setShowAdd(true)}
            className="text-brand-400 text-sm hover:underline"
          >
            Add your first keywords →
          </button>
        </div>
      ) : (
        <div className="bg-surface-100 border border-zinc-800/60 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800/60">
                <th
                  className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-semibold cursor-pointer hover:text-zinc-300"
                  onClick={() => toggleSort("keyword")}
                >
                  <span className="flex items-center gap-1">
                    Keyword <ArrowUpDown size={10} />
                  </span>
                </th>
                <th
                  className="text-center px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-semibold cursor-pointer hover:text-zinc-300 w-24"
                  onClick={() => toggleSort("position")}
                >
                  <span className="flex items-center justify-center gap-1">
                    Position <ArrowUpDown size={10} />
                  </span>
                </th>
                <th
                  className="text-center px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-semibold cursor-pointer hover:text-zinc-300 w-24"
                  onClick={() => toggleSort("change")}
                >
                  <span className="flex items-center justify-center gap-1">
                    Change <ArrowUpDown size={10} />
                  </span>
                </th>
                <th className="text-center px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-semibold w-24">
                  Volume
                </th>
                <th className="text-right px-4 py-3 text-[10px] uppercase tracking-[0.12em] text-zinc-500 font-semibold w-16">
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((kw) => {
                const change = kw.position_change;
                const isUp = change !== null && change > 0;
                const isDown = change !== null && change < 0;
                return (
                  <tr
                    key={kw.id}
                    className="border-b border-zinc-800/30 hover:bg-surface-200/40 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span className="text-sm text-zinc-200">{kw.keyword}</span>
                      {kw.tags && (
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-surface-300 text-zinc-500">
                          {kw.tags}
                        </span>
                      )}
                    </td>
                    <td className="text-center px-4 py-3">
                      <span
                        className={cn(
                          "font-mono text-sm font-medium",
                          kw.latest_position && kw.latest_position <= 3
                            ? "text-emerald-400"
                            : kw.latest_position && kw.latest_position <= 10
                            ? "text-brand-300"
                            : "text-zinc-400"
                        )}
                      >
                        {formatPosition(kw.latest_position)}
                      </span>
                    </td>
                    <td className="text-center px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 font-mono text-xs font-medium px-2 py-0.5 rounded-full",
                          isUp && "text-emerald-400 bg-emerald-500/10",
                          isDown && "text-red-400 bg-red-500/10",
                          !isUp && !isDown && "text-zinc-500"
                        )}
                      >
                        {isUp && <TrendingUp size={11} />}
                        {isDown && <TrendingDown size={11} />}
                        {!isUp && !isDown && <Minus size={11} />}
                        {formatChange(change)}
                      </span>
                    </td>
                    <td className="text-center px-4 py-3 text-xs text-zinc-500 font-mono">
                      {kw.search_volume ?? "—"}
                    </td>
                    <td className="text-right px-4 py-3">
                      <button
                        onClick={() => handleDelete(kw.id)}
                        className="p-1.5 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition"
                      >
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Generates demo rank data until real API is connected
function generateDemoRankData(keywords: string[]) {
  const domains = ["your-site.com", "competitor-1.com", "competitor-2.com"];
  const days = 14;
  const data = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const point: Record<string, any> = {
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    };
    domains.forEach((domain, di) => {
      const base = 5 + di * 8;
      point[domain] = Math.max(1, base + Math.round(Math.sin(i * 0.5 + di) * 4 + (Math.random() - 0.5) * 3));
    });
    data.push(point);
  }
  return data;
}
