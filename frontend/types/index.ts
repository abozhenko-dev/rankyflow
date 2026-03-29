// ── Auth ──────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  plan: "free" | "starter" | "pro" | "agency";
  is_verified: boolean;
  auth_provider: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ── Projects ──────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  domain: string;
  description: string | null;
  target_country: string;
  target_language: string;
  track_mobile: boolean;
  track_desktop: boolean;
  gsc_property_url: string | null;
  ga4_property_id: string | null;
  is_active: boolean;
  created_at: string;
  competitors_count: number;
  keywords_count: number;
}

// ── Competitors ───────────────────────────────────────

export interface Competitor {
  id: string;
  project_id: string;
  domain: string;
  name: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

// ── Keywords ──────────────────────────────────────────

export interface Keyword {
  id: string;
  project_id: string;
  keyword: string;
  search_volume: number | null;
  difficulty: number | null;
  tags: string | null;
  is_active: boolean;
  created_at: string;
  latest_position: number | null;
  position_change: number | null;
}

// ── Rank History ──────────────────────────────────────

export interface RankEntry {
  keyword: string;
  domain: string;
  position: number | null;
  position_change: number | null;
  device: string;
  checked_date: string;
  gsc_clicks: number | null;
  gsc_impressions: number | null;
}

// ── Change Detection ──────────────────────────────────

export interface ChangeLogEntry {
  id: string;
  tracked_page_url: string;
  competitor_name: string;
  severity: "minor" | "moderate" | "major";
  change_type: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  ai_summary: string | null;
  detected_at: string;
}

// ── GEO / AI Visibility ──────────────────────────────

export interface LLMPrompt {
  id: string;
  prompt_text: string;
  intent: string;
  tags: string | null;
  is_active: boolean;
  is_auto_generated: boolean;
  created_at: string;
}

export interface VisibilitySnapshot {
  platform: string;
  mention_rate: number;
  citation_rate: number;
  recommendation_rate: number;
  avg_position: number | null;
  share_of_voice: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  snapshot_date: string;
}

// ── Agent Runs ────────────────────────────────────────

export interface AgentRun {
  id: string;
  project_id: string;
  agent_type: string;
  status: string;
  items_processed: number;
  items_failed: number;
  duration_seconds: number | null;
  api_cost_usd: number | null;
  result_summary: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}
