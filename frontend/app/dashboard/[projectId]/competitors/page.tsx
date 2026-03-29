"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { competitors as compApi } from "@/lib/api";
import type { Competitor } from "@/types";
import { Plus, Trash2, Loader2, Globe, ExternalLink } from "lucide-react";

export default function CompetitorsPage() {
  const { projectId } = useParams() as { projectId: string };
  const [comps, setComps] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newDomain, setNewDomain] = useState("");
  const [newName, setNewName] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    loadCompetitors();
  }, [projectId]);

  async function loadCompetitors() {
    try {
      const data = await compApi.list(projectId);
      setComps(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    if (!newDomain || !newName) return;
    setAdding(true);
    try {
      await compApi.add(projectId, { domain: newDomain, name: newName });
      setNewDomain("");
      setNewName("");
      setShowAdd(false);
      loadCompetitors();
    } catch (e) {
      console.error(e);
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await compApi.remove(id);
      setComps((prev) => prev.filter((c) => c.id !== id));
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl text-zinc-100">Competitors</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            {comps.length} tracked competitor{comps.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus size={14} />
          Add Competitor
        </button>
      </div>

      {/* Add modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-surface-100 border border-zinc-800 rounded-2xl p-6 w-full max-w-md animate-slide-up">
            <h2 className="font-display text-xl mb-4">Add Competitor</h2>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Display name (e.g. Ahrefs)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-4 py-2.5 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <input
                type="text"
                placeholder="Domain (e.g. ahrefs.com)"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                className="w-full px-4 py-2.5 bg-surface-200 border border-zinc-700 rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button
                onClick={() => setShowAdd(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={adding || !newDomain || !newName}
                className="px-5 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
              >
                {adding && <Loader2 size={14} className="animate-spin" />}
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Competitors list */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 size={24} className="animate-spin text-zinc-500" />
        </div>
      ) : comps.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-zinc-800 rounded-2xl">
          <Globe size={40} className="mx-auto text-zinc-700 mb-4" />
          <p className="text-zinc-400 mb-2">No competitors added yet</p>
          <button
            onClick={() => setShowAdd(true)}
            className="text-brand-400 text-sm hover:underline"
          >
            Add your first competitor →
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {comps.map((comp) => (
            <div
              key={comp.id}
              className="bg-surface-100 border border-zinc-800/60 rounded-xl p-5 hover:border-zinc-700/60 transition group"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-surface-200 flex items-center justify-center">
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${comp.domain}&sz=32`}
                      alt=""
                      className="w-5 h-5 rounded"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </div>
                  <div>
                    <h3 className="font-medium text-zinc-200">{comp.name}</h3>
                    <p className="text-xs text-zinc-500 font-mono flex items-center gap-1">
                      {comp.domain}
                      <a
                        href={`https://${comp.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-zinc-600 hover:text-brand-400"
                      >
                        <ExternalLink size={10} />
                      </a>
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(comp.id)}
                  className="p-1.5 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition opacity-0 group-hover:opacity-100"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {comp.notes && (
                <p className="text-xs text-zinc-500 mt-3 pl-[52px]">
                  {comp.notes}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
