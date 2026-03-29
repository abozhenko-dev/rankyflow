/**
 * API client — typed HTTP wrapper for the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

// ── Token management ─────────────────────────────────

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function setTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// ── Core fetch ───────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Try refresh
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getToken()}`;
      const retry = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
        ...options,
        headers,
      });
      if (!retry.ok) throw new ApiError(retry.status, await retry.text());
      if (retry.status === 204) return undefined as T;
      return retry.json();
    }
    clearTokens();
    window.location.href = "/auth/login";
    throw new ApiError(401, "Session expired");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}${API_PREFIX}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

class ApiError extends Error {
  status: number;
  constructor(status: number, body: string) {
    super(`API ${status}: ${body}`);
    this.status = status;
  }
}

// ── Auth ─────────────────────────────────────────────

export const auth = {
  register: (email: string, password: string, full_name?: string) =>
    apiFetch<any>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: async (email: string, password: string) => {
    const data = await apiFetch<any>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  logout: () => {
    clearTokens();
    window.location.href = "/auth/login";
  },

  me: () => apiFetch<any>("/auth/me"),
};

// ── Projects ─────────────────────────────────────────

export const projects = {
  list: () => apiFetch<any[]>("/projects"),

  get: (id: string) => apiFetch<any>(`/projects/${id}`),

  create: (data: { name: string; domain: string; target_country?: string }) =>
    apiFetch<any>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Record<string, any>) =>
    apiFetch<any>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/projects/${id}`, { method: "DELETE" }),
};

// ── Competitors ──────────────────────────────────────

export const competitors = {
  list: (projectId: string) =>
    apiFetch<any[]>(`/projects/${projectId}/competitors`),

  add: (projectId: string, data: { domain: string; name: string }) =>
    apiFetch<any>(`/projects/${projectId}/competitors`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  remove: (id: string) =>
    apiFetch<void>(`/competitors/${id}`, { method: "DELETE" }),
};

// ── Keywords ─────────────────────────────────────────

export const keywords = {
  list: (projectId: string) =>
    apiFetch<any[]>(`/projects/${projectId}/keywords`),

  add: (projectId: string, keyword: string, tags?: string) =>
    apiFetch<any>(`/projects/${projectId}/keywords`, {
      method: "POST",
      body: JSON.stringify({ keyword, tags }),
    }),

  bulkAdd: (projectId: string, keywords: string[]) =>
    apiFetch<any[]>(`/projects/${projectId}/keywords/bulk`, {
      method: "POST",
      body: JSON.stringify({ keywords }),
    }),

  remove: (id: string) =>
    apiFetch<void>(`/keywords/${id}`, { method: "DELETE" }),
};

// ── GEO ──────────────────────────────────────────────

export const geo = {
  listPrompts: (projectId: string) =>
    apiFetch<any[]>(`/geo/projects/${projectId}/prompts`),

  addPrompt: (projectId: string, prompt_text: string, intent?: string) =>
    apiFetch<any>(`/geo/projects/${projectId}/prompts`, {
      method: "POST",
      body: JSON.stringify({ prompt_text, intent: intent || "commercial" }),
    }),

  bulkAddPrompts: (projectId: string, prompts: string[]) =>
    apiFetch<any[]>(`/geo/projects/${projectId}/prompts/bulk`, {
      method: "POST",
      body: JSON.stringify({ prompts }),
    }),

  removePrompt: (id: string) =>
    apiFetch<void>(`/geo/prompts/${id}`, { method: "DELETE" }),

  getVisibility: (projectId: string, platform?: string) =>
    apiFetch<any[]>(
      `/geo/projects/${projectId}/visibility${platform ? `?platform=${platform}` : ""}`
    ),
};

// ── Agents ───────────────────────────────────────────

export const agents = {
  runAll: (projectId: string) =>
    apiFetch<any>(`/agents/projects/${projectId}/run-all`, { method: "POST" }),

  runSingle: (projectId: string, agentType: string) =>
    apiFetch<any>(`/agents/projects/${projectId}/run/${agentType}`, {
      method: "POST",
    }),

  listRuns: (projectId: string, agentType?: string) =>
    apiFetch<any[]>(
      `/agents/projects/${projectId}/runs${agentType ? `?agent_type=${agentType}` : ""}`
    ),
};

// ── Ranks ────────────────────────────────────────────

export const ranks = {
  history: (projectId: string, params?: { keyword_id?: string; domain?: string; device?: string; days?: number }) => {
    const qs = new URLSearchParams();
    if (params?.keyword_id) qs.set("keyword_id", params.keyword_id);
    if (params?.domain) qs.set("domain", params.domain);
    if (params?.device) qs.set("device", params.device);
    if (params?.days) qs.set("days", String(params.days));
    return apiFetch<any[]>(`/ranks/projects/${projectId}/history?${qs}`);
  },

  chart: (projectId: string, keywordId: string, device?: string, days?: number) => {
    const qs = new URLSearchParams({ keyword_id: keywordId });
    if (device) qs.set("device", device);
    if (days) qs.set("days", String(days));
    return apiFetch<{ dates: string[]; series: Record<string, (number | null)[]> }>(
      `/ranks/projects/${projectId}/chart?${qs}`
    );
  },

// ── Data (Ranks, Changes, Stats) ─────────────────────

export const data = {
  rankHistory: (projectId: string, keywordId: string, days?: number, device?: string) => {
    const qs = new URLSearchParams();
    if (days) qs.set("days", String(days));
    if (device) qs.set("device", device);
    return apiFetch<any>(`/data/projects/${projectId}/rank-history/${keywordId}?${qs}`);
  },

  changes: (projectId: string, severity?: string, limit?: number) => {
    const qs = new URLSearchParams();
    if (severity) qs.set("severity", severity);
    if (limit) qs.set("limit", String(limit));
    return apiFetch<any[]>(`/data/projects/${projectId}/changes?${qs}`);
  },

  stats: (projectId: string) =>
    apiFetch<any>(`/data/projects/${projectId}/stats`),
};
