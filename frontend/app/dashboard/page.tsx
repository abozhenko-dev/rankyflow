"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { projects as projectsApi } from "@/lib/api";
import type { Project } from "@/types";
import StatCard from "@/components/ui/StatCard";
import {
  FolderOpen,
  Plus,
  Globe,
  KeyRound,
  Users,
  ArrowRight,
  Loader2,
} from "lucide-react";

export default function DashboardPage() {
  const [projectsList, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDomain, setNewDomain] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      const data = await projectsApi.list();
      setProjects(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!newName || !newDomain) return;
    setCreating(true);
    setCreateError("");
    try {
      await projectsApi.create({ name: newName, domain: newDomain });
      setNewName("");
      setNewDomain("");
      setShowCreate(false);
      loadProjects();
    } catch (e: any) {
      const msg = e?.message || "Failed to create project";
      try {
        const parsed = JSON.parse(msg.replace(/^API \d+: /, ""));
        setCreateError(parsed.detail || msg);
      } catch {
        setCreateError(msg);
      }
    } finally {
      setCreating(false);
    }
  }

  const totalKeywords = projectsList.reduce((s, p) => s + p.keywords_count, 0);
  const totalCompetitors = projectsList.reduce((s, p) => s + p.competitors_count, 0);

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl text-zinc-100">Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Your SEO & AI visibility command center
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus size={16} />
          New Project
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Projects"
          value={projectsList.length}
          icon={FolderOpen}
        />
        <StatCard
          label="Keywords tracked"
          value={totalKeywords}
          icon={KeyRound}
        />
        <StatCard
          label="Competitors"
          value={totalCompetitors}
          icon={Users}
        />
        <StatCard
          label="Next scan"
          value="06:00 UTC"
          icon={Globe}
        />
      </div>

      {/* Create project modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-surface-100 border border-zinc-800 rounded-2xl p-6 w-full max-w-md animate-slide-up">
            <h2 className="font-display text-xl mb-4">Create Project</h2>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Project name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-4 py-2.5 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <input
                type="text"
                placeholder="Domain (e.g. example.com)"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                className="w-full px-4 py-2.5 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            {createError && (
              <p className="text-red-400 text-sm mt-3">{createError}</p>
            )}
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !newName || !newDomain}
                className="px-5 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
              >
                {creating && <Loader2 size={14} className="animate-spin" />}
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Projects grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-zinc-500" />
        </div>
      ) : projectsList.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-zinc-800 rounded-2xl">
          <FolderOpen size={40} className="mx-auto text-zinc-700 mb-4" />
          <p className="text-zinc-400 mb-2">No projects yet</p>
          <button
            onClick={() => setShowCreate(true)}
            className="text-brand-400 text-sm hover:underline"
          >
            Create your first project →
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {projectsList.map((project) => (
            <Link
              key={project.id}
              href={`/dashboard/${project.id}/keywords`}
              className="group bg-surface-100 border border-zinc-800/60 rounded-xl p-5 hover:border-brand-600/30 hover:glow-brand transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-zinc-100 group-hover:text-brand-300 transition-colors">
                    {project.name}
                  </h3>
                  <p className="text-xs text-zinc-500 font-mono mt-0.5">
                    {project.domain}
                  </p>
                </div>
                <ArrowRight
                  size={16}
                  className="text-zinc-600 group-hover:text-brand-400 group-hover:translate-x-0.5 transition-all"
                />
              </div>
              <div className="flex items-center gap-4 text-xs text-zinc-500">
                <span className="flex items-center gap-1.5">
                  <KeyRound size={12} />
                  {project.keywords_count} keywords
                </span>
                <span className="flex items-center gap-1.5">
                  <Users size={12} />
                  {project.competitors_count} competitors
                </span>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-surface-200 text-zinc-500">
                  {project.target_country}
                </span>
                {project.gsc_property_url && (
                  <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400">
                    GSC
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
