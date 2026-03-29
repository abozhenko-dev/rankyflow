"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Sidebar from "@/components/dashboard/Sidebar";
import { projects as projectsApi } from "@/lib/api";
import type { Project } from "@/types";
import { Loader2 } from "lucide-react";

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<Project | null>(null);

  useEffect(() => {
    projectsApi.get(projectId).then(setProject).catch(console.error);
  }, [projectId]);

  return (
    <div className="flex min-h-screen">
      <Sidebar projectId={projectId} />
      <main className="flex-1 ml-[240px]">
        {/* Project header bar */}
        <div className="border-b border-zinc-800/60 bg-surface-50/80 backdrop-blur-sm sticky top-0 z-30">
          <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center gap-3">
            {project ? (
              <>
                <div className="w-7 h-7 rounded-md bg-brand-600/20 flex items-center justify-center text-brand-400 text-xs font-bold">
                  {project.name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <span className="text-sm font-medium text-zinc-200">
                    {project.name}
                  </span>
                  <span className="text-xs text-zinc-500 ml-2 font-mono">
                    {project.domain}
                  </span>
                </div>
                <div className="ml-auto flex items-center gap-2 text-[10px] uppercase tracking-wider">
                  <span className="px-2 py-0.5 rounded bg-surface-200 text-zinc-500">
                    {project.target_country}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-200 text-zinc-500">
                    {project.keywords_count} kw
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-200 text-zinc-500">
                    {project.competitors_count} comp
                  </span>
                </div>
              </>
            ) : (
              <Loader2 size={16} className="animate-spin text-zinc-500" />
            )}
          </div>
        </div>

        <div className="max-w-[1400px] mx-auto px-6 py-6">{children}</div>
      </main>
    </div>
  );
}
