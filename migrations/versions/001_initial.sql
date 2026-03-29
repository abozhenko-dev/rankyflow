-- RankyFlow Initial Migration
-- Run against Supabase PostgreSQL via SQL Editor

-- Enums
CREATE TYPE plan_tier AS ENUM ('free', 'starter', 'pro', 'agency');
CREATE TYPE change_severity AS ENUM ('minor', 'moderate', 'major');
CREATE TYPE agent_type AS ENUM ('rank_tracker', 'change_detection', 'google_data', 'geo_visibility', 'analysis', 'alert_report');
CREATE TYPE run_status AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE llm_platform AS ENUM ('chatgpt', 'claude', 'perplexity', 'gemini', 'deepseek');
CREATE TYPE prompt_intent AS ENUM ('informational', 'commercial', 'transactional', 'navigational');
CREATE TYPE mention_sentiment AS ENUM ('positive', 'neutral', 'negative');

-- Users
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(128),
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    auth_provider VARCHAR(20) DEFAULT 'email',
    google_access_token TEXT,
    google_refresh_token TEXT,
    plan plan_tier DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);

-- Projects
CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    description TEXT,
    gsc_property_url VARCHAR(500),
    ga4_property_id VARCHAR(50),
    target_country VARCHAR(5) DEFAULT 'US',
    target_language VARCHAR(5) DEFAULT 'en',
    track_mobile BOOLEAN DEFAULT true,
    track_desktop BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_projects_owner ON projects(owner_id);

-- Competitors
CREATE TABLE competitors (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_competitors_project ON competitors(project_id);

-- Keywords
CREATE TABLE keywords (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    keyword VARCHAR(500) NOT NULL,
    search_volume INTEGER,
    difficulty FLOAT,
    tags VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_keywords_project ON keywords(project_id);

-- Rank History
CREATE TABLE rank_history (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    keyword_id VARCHAR(36) NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    position INTEGER,
    url VARCHAR(2000),
    device VARCHAR(10) DEFAULT 'desktop',
    serp_features TEXT,
    position_change INTEGER,
    gsc_clicks INTEGER,
    gsc_impressions INTEGER,
    gsc_ctr FLOAT,
    gsc_position FLOAT,
    checked_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(keyword_id, domain, device, checked_date)
);
CREATE INDEX idx_rank_keyword ON rank_history(keyword_id);
CREATE INDEX idx_rank_domain ON rank_history(domain);
CREATE INDEX idx_rank_date ON rank_history(checked_date);

-- Tracked Pages
CREATE TABLE tracked_pages (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    competitor_id VARCHAR(36) NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    url VARCHAR(2000) NOT NULL,
    label VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_tracked_competitor ON tracked_pages(competitor_id);

-- Page Snapshots
CREATE TABLE page_snapshots (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tracked_page_id VARCHAR(36) NOT NULL REFERENCES tracked_pages(id) ON DELETE CASCADE,
    title VARCHAR(1000),
    meta_description VARCHAR(2000),
    h1 VARCHAR(1000),
    headings_json TEXT,
    word_count INTEGER,
    internal_links_count INTEGER,
    external_links_count INTEGER,
    schema_markup TEXT,
    content_hash VARCHAR(64),
    raw_text TEXT,
    captured_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_snapshot_page ON page_snapshots(tracked_page_id);

-- Change Log
CREATE TABLE change_log (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tracked_page_id VARCHAR(36) NOT NULL REFERENCES tracked_pages(id) ON DELETE CASCADE,
    snapshot_before_id VARCHAR(36) REFERENCES page_snapshots(id) ON DELETE SET NULL,
    snapshot_after_id VARCHAR(36) REFERENCES page_snapshots(id) ON DELETE SET NULL,
    severity change_severity DEFAULT 'minor',
    change_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    diff_html TEXT,
    ai_summary TEXT,
    ai_impact_score FLOAT,
    detected_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_change_page ON change_log(tracked_page_id);

-- Agent Runs
CREATE TABLE agent_runs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) NOT NULL,
    agent_type agent_type NOT NULL,
    status run_status DEFAULT 'pending',
    items_processed INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    duration_seconds FLOAT,
    api_cost_usd FLOAT,
    result_summary TEXT,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX idx_agent_project ON agent_runs(project_id);

-- LLM Prompts (GEO)
CREATE TABLE llm_prompts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    intent prompt_intent DEFAULT 'commercial',
    tags VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_auto_generated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_prompt_project ON llm_prompts(project_id);

-- LLM Responses (GEO)
CREATE TABLE llm_responses (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    prompt_id VARCHAR(36) NOT NULL REFERENCES llm_prompts(id) ON DELETE CASCADE,
    platform llm_platform NOT NULL,
    response_text TEXT NOT NULL,
    cited_urls TEXT,
    cited_domains TEXT,
    source_count INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    api_cost_usd FLOAT,
    checked_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(prompt_id, platform, checked_date)
);
CREATE INDEX idx_response_prompt ON llm_responses(prompt_id);
CREATE INDEX idx_response_date ON llm_responses(checked_date);

-- LLM Mentions (GEO)
CREATE TABLE llm_mentions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    response_id VARCHAR(36) NOT NULL REFERENCES llm_responses(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    brand_name VARCHAR(255) NOT NULL,
    is_mentioned BOOLEAN DEFAULT false,
    is_cited BOOLEAN DEFAULT false,
    is_recommended BOOLEAN DEFAULT false,
    position_in_list INTEGER,
    mention_count INTEGER DEFAULT 0,
    sentiment mention_sentiment,
    sentiment_snippet TEXT,
    is_own_brand BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_mention_response ON llm_mentions(response_id);
CREATE INDEX idx_mention_domain ON llm_mentions(domain);

-- GEO Visibility Snapshots
CREATE TABLE geo_visibility_snapshots (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    platform llm_platform NOT NULL,
    total_prompts_checked INTEGER DEFAULT 0,
    mention_rate FLOAT DEFAULT 0,
    citation_rate FLOAT DEFAULT 0,
    recommendation_rate FLOAT DEFAULT 0,
    avg_position FLOAT,
    share_of_voice FLOAT DEFAULT 0,
    positive_pct FLOAT DEFAULT 0,
    neutral_pct FLOAT DEFAULT 0,
    negative_pct FLOAT DEFAULT 0,
    top_source_domains TEXT,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(project_id, platform, snapshot_date)
);
CREATE INDEX idx_geo_project ON geo_visibility_snapshots(project_id);
CREATE INDEX idx_geo_date ON geo_visibility_snapshots(snapshot_date);
