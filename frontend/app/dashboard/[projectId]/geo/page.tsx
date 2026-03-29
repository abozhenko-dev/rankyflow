"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { geo } from "@/lib/api";
import type { LLMPrompt, VisibilitySnapshot } from "@/types";
import { cn, formatPercent, platformIcon } from "@/lib/utils";
import {
  Plus,
  Trash2,
  Loader2,
  Eye,
  Quote,
  ThumbsUp,
  Target,
  Crown,
  Upload,
} from "lucide-react";
import VisibilityChart from "@/components/charts/VisibilityChart";
import DistributionChart from "@/components/charts/DistributionChart";

const PLATFORM_META: Record<string, { name: string; color: string; bg: string }> = {
  chatgpt:    { name: "ChatGPT",    color: "text-emerald-400", bg: "bg-emerald-500/10" },
  perplexity: { name: "Perplexity", color: "text-blue-400",    bg: "bg-blue-500/10" },
  claude:     { name: "Claude",     color: "text-amber-400",   bg: "bg-amber-500/10" },
  gemini:     { name: "Gemini",     color: "text-purple-400",  bg: "bg-purple-500/10" },
  deepseek:   { name: "DeepSeek",   color: "text-cyan-400",    bg: "bg-cyan-500/10" },
};

export default function GEOPage() {
  const { projectId } = useParams() as { projectId: string };
  const [prompts, setPrompts] = useState<LLMPrompt[]>([]);
  const [snapshots, setSnapshots] = useState<VisibilitySnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview" | "prompts">("overview");
  const [showAdd, setShowAdd] = useState(false);
  const [newPrompt, setNewPrompt] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [bulkMode, setBulkMode] = useState(false);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    loadData();
  }, [projectId]);

  async function loadData() {
    try {
      const [p, s] = await Promise.all([
        geo.listPrompts(projectId).catch(() => []),
        geo.getVisibility(projectId).catch(() => []),
      ]);
      setPrompts(p);
      setSnapshots(s);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddPrompts() {
    setAdding(true);
    try {
      if (bulkMode) {
        const lines = bulkText.split("\n").map(l => l.trim()).filter(Boolean);
        if (lines.length) await geo.bulkAddPrompts(projectId, lines);
        setBulkText("");
      } else {
        if (newPrompt.trim()) await geo.addPrompt(projectId, newPrompt.trim());
        setNewPrompt("");
      }
      setShowAdd(false);
      loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setAdding(false);
    }
  }

  async function handleDeletePrompt(id: string) {
    try {
      await geo.removePrompt(id);
      setPrompts(prev => prev.filter(p => p.id !== id));
    } catch (e) {
      console.error(e);
    }
  }

  // Group latest snapshots by platform
  const latestByPlatform: Record<string, VisibilitySnapshot> = {};
  for (const s of snapshots) {
    if (!latestByPlatform[s.platform] || s.snapshot_date > latestByPlatform[s.platform].snapshot_date) {
      latestByPlatform[s.platform] = s;
    }
  }

  // Compute overall metrics
  const platforms = Object.values(latestByPlatform);
  const avgMention = platforms.length
    ? platforms.reduce((s, p) => s + p.mention_rate, 0) / platforms.length
    : 0;
  const avgSoV = platforms.length
    ? platforms.reduce((s, p) => s + p.share_of_voice, 0) / platforms.length
    : 0;

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 size={24} className="animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl text-zinc-100">
            AI Visibility
            <span className="text-xs font-body font-normal text-brand-400 ml-2 px-2 py-0.5 rounded-full bg-brand-600/10 border border-brand-600/20">
              GEO
            </span>
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Track how AI platforms mention your brand vs competitors
          </p>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 bg-surface-100 rounded-lg p-1 border border-zinc-800/60 w-fit mb-6">
        <button
          onClick={() => setTab("overview")}
          className={cn(
            "px-4 py-2 text-sm rounded-md transition",
            tab === "overview" ? "bg-brand-600 text-white" : "text-zinc-400 hover:text-zinc-200"
          )}
        >
          <Eye size={14} className="inline mr-1.5" />
          Overview
        </button>
        <button
          onClick={() => setTab("prompts")}
          className={cn(
            "px-4 py-2 text-sm rounded-md transition",
            tab === "prompts" ? "bg-brand-600 text-white" : "text-zinc-400 hover:text-zinc-200"
          )}
        >
          <Quote size={14} className="inline mr-1.5" />
          Prompts ({prompts.length})
        </button>
      </div>

      {/* ═══ OVERVIEW TAB ═══ */}
      {tab === "overview" && (
        <>
          {/* Overall stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Eye size={14} className="text-brand-400" />
                <span className="text-xs uppercase tracking-wider text-zinc-500">Avg Mention Rate</span>
              </div>
              <div className="text-2xl font-semibold text-zinc-100">{formatPercent(avgMention)}</div>
              <p className="text-xs text-zinc-500 mt-1">across {platforms.length} platforms</p>
            </div>
            <div className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Crown size={14} className="text-amber-400" />
                <span className="text-xs uppercase tracking-wider text-zinc-500">Share of Voice</span>
              </div>
              <div className="text-2xl font-semibold text-zinc-100">{formatPercent(avgSoV)}</div>
              <p className="text-xs text-zinc-500 mt-1">vs tracked competitors</p>
            </div>
            <div className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Target size={14} className="text-emerald-400" />
                <span className="text-xs uppercase tracking-wider text-zinc-500">Prompts Tracked</span>
              </div>
              <div className="text-2xl font-semibold text-zinc-100">{prompts.length}</div>
              <p className="text-xs text-zinc-500 mt-1">active queries</p>
            </div>
          </div>

          {/* Charts row */}
          {platforms.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <VisibilityChart
                data={generateDemoVisibilityTrend(Object.keys(latestByPlatform))}
                platforms={Object.keys(latestByPlatform)}
                metric="mention_rate"
              />
              <DistributionChart
                data={[
                  { name: "Your brand", value: avgSoV, isOwn: true },
                  { name: "Competitor A", value: 0.28 },
                  { name: "Competitor B", value: 0.19 },
                  { name: "Competitor C", value: 0.12 },
                ]}
                label="Share of Voice — All Platforms"
              />
            </div>
          )}

          {/* Platform cards */}
          {platforms.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-zinc-800 rounded-2xl">
              <Eye size={40} className="mx-auto text-zinc-700 mb-4" />
              <p className="text-zinc-400 mb-2">No visibility data yet</p>
              <p className="text-xs text-zinc-600">
                Add prompts and wait for the weekly GEO scan to run
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {Object.entries(latestByPlatform).map(([platform, data]) => {
                const meta = PLATFORM_META[platform] || { name: platform, color: "text-zinc-400", bg: "bg-zinc-500/10" };
                return (
                  <div
                    key={platform}
                    className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5 hover:border-zinc-700/60 transition"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center text-lg", meta.bg)}>
                        {platformIcon(platform)}
                      </div>
                      <div>
                        <h3 className={cn("font-medium", meta.color)}>{meta.name}</h3>
                        <p className="text-[10px] text-zinc-600">{data.snapshot_date}</p>
                      </div>
                    </div>

                    <div className="space-y-2.5">
                      <MetricRow label="Mention Rate" value={formatPercent(data.mention_rate)} />
                      <MetricRow label="Citation Rate" value={formatPercent(data.citation_rate)} />
                      <MetricRow label="Recommended" value={formatPercent(data.recommendation_rate)} />
                      <MetricRow label="Avg Position" value={data.avg_position ? `#${data.avg_position.toFixed(1)}` : "—"} />
                      <MetricRow label="Share of Voice" value={formatPercent(data.share_of_voice)} highlight />
                    </div>

                    {/* Sentiment bar */}
                    <div className="mt-4 pt-3 border-t border-zinc-800/40">
                      <div className="flex items-center gap-1 h-2 rounded-full overflow-hidden">
                        <div className="bg-emerald-500 h-full rounded-l-full" style={{ width: `${data.positive_pct * 100}%` }} />
                        <div className="bg-zinc-500 h-full" style={{ width: `${data.neutral_pct * 100}%` }} />
                        <div className="bg-red-500 h-full rounded-r-full" style={{ width: `${data.negative_pct * 100}%` }} />
                      </div>
                      <div className="flex justify-between mt-1.5 text-[10px] text-zinc-600">
                        <span className="text-emerald-500">{formatPercent(data.positive_pct)} pos</span>
                        <span>{formatPercent(data.neutral_pct)} neutral</span>
                        <span className="text-red-500">{formatPercent(data.negative_pct)} neg</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ═══ PROMPTS TAB ═══ */}
      {tab === "prompts" && (
        <>
          <div className="flex justify-end mb-4">
            <button
              onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg transition"
            >
              <Plus size={14} />
              Add Prompts
            </button>
          </div>

          {/* Add modal */}
          {showAdd && (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
              <div className="bg-surface-100 border border-zinc-800 rounded-2xl p-6 w-full max-w-lg animate-slide-up">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-display text-xl">Add Prompts</h2>
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
                <p className="text-xs text-zinc-500 mb-3">
                  Write questions your target audience would ask AI chatbots.
                  E.g.: "What is the best SEO tool for agencies?"
                </p>
                {bulkMode ? (
                  <textarea
                    placeholder="One prompt per line..."
                    value={bulkText}
                    onChange={(e) => setBulkText(e.target.value)}
                    rows={8}
                    className="w-full px-4 py-3 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                ) : (
                  <input
                    type="text"
                    placeholder="Enter a prompt..."
                    value={newPrompt}
                    onChange={(e) => setNewPrompt(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddPrompts()}
                    className="w-full px-4 py-2.5 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                )}
                <div className="flex justify-end gap-3 mt-5">
                  <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm text-zinc-400">
                    Cancel
                  </button>
                  <button
                    onClick={handleAddPrompts}
                    disabled={adding}
                    className="px-5 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
                  >
                    {adding && <Loader2 size={14} className="animate-spin" />}
                    Add
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Prompts list */}
          {prompts.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-zinc-800 rounded-2xl">
              <Quote size={40} className="mx-auto text-zinc-700 mb-4" />
              <p className="text-zinc-400 mb-2">No prompts yet</p>
              <p className="text-xs text-zinc-600 mb-4">
                Add questions your customers ask AI chatbots
              </p>
              <button
                onClick={() => setShowAdd(true)}
                className="text-brand-400 text-sm hover:underline"
              >
                Add your first prompts →
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {prompts.map((prompt) => (
                <div
                  key={prompt.id}
                  className="bg-surface-100 border border-zinc-800/60 rounded-xl px-5 py-3.5 flex items-center gap-4 group hover:border-zinc-700/60 transition"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-zinc-200 truncate">
                      "{prompt.prompt_text}"
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface-200 text-zinc-500">
                        {prompt.intent}
                      </span>
                      {prompt.is_auto_generated && (
                        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-brand-600/10 text-brand-400">
                          auto
                        </span>
                      )}
                      {prompt.tags && (
                        <span className="text-[10px] text-zinc-600">{prompt.tags}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeletePrompt(prompt.id)}
                    className="p-1.5 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Demo trend data until real API history is available
function generateDemoVisibilityTrend(platforms: string[]) {
  const weeks = 8;
  const data = [];
  for (let i = weeks - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i * 7);
    const point: Record<string, any> = {
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    };
    platforms.forEach((p, pi) => {
      const base = 0.15 + pi * 0.08;
      point[p] = Math.min(1, Math.max(0, base + (weeks - i) * 0.02 + (Math.random() - 0.5) * 0.06));
    });
    data.push(point);
  }
  return data;
}

function MetricRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-zinc-500">{label}</span>
      <span
        className={cn(
          "text-sm font-mono font-medium",
          highlight ? "text-brand-300" : "text-zinc-300"
        )}
      >
        {value}
      </span>
    </div>
  );
}
