# Deployment Guide — SEO Competitor Tracker

## Prerequisites

- GitHub account with the repo pushed
- Railway account (https://railway.app)
- Vercel account (https://vercel.com)
- DataForSEO account (https://dataforseo.com) — get login/password
- Supabase project (https://supabase.com) — get DB URL + keys
- Anthropic API key (https://console.anthropic.com)
- (Optional for GEO) OpenAI, Perplexity, Gemini, DeepSeek API keys

---

## Step 1: Push to GitHub

```bash
cd seo-tracker
git init
git add .
git commit -m "Initial commit: full backend + frontend"
git remote add origin git@github.com:YOUR_USER/seo-tracker.git
git push -u origin main
```

---

## Step 2: Supabase (Database)

1. Create new project at https://supabase.com
2. Go to **Settings > Database** → copy:
   - `Connection string (URI)` — this is your `DATABASE_URL_SYNC`
   - Replace `postgresql://` with `postgresql+asyncpg://` for `DATABASE_URL`
3. Run migrations locally pointing to Supabase:
   ```bash
   # Set DATABASE_URL in .env to Supabase
   alembic upgrade head
   ```

---

## Step 3: Railway (Backend)

### 3a. Create project
1. Go to https://railway.app → **New Project → Deploy from GitHub repo**
2. Select your repo

### 3b. Add Redis
1. Click **+ New** → **Database** → **Redis**
2. Copy the `REDIS_URL` from the Redis service

### 3c. Configure API service
1. Select the deployed service → **Settings**:
   - **Root directory:** `/` (default)
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check:** `/health`
2. Go to **Variables** and add ALL from `.env.example`:

```
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-a-random-64-char-string>
DATABASE_URL=postgresql+asyncpg://...@supabase.../postgres
DATABASE_URL_SYNC=postgresql://...@supabase.../postgres
REDIS_URL=<from-railway-redis>
JWT_SECRET_KEY=<generate-another-random-string>
DATAFORSEO_LOGIN=<your-login>
DATAFORSEO_PASSWORD=<your-password>
ANTHROPIC_API_KEY=sk-ant-...
CORS_ORIGINS=["https://your-app.vercel.app"]
RESEND_API_KEY=re_...
```

Add GEO keys if using AI Visibility:
```
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=sk-...
```

### 3d. Add Celery Worker service
1. Click **+ New** → **GitHub repo** → same repo
2. Settings:
   - **Start command:** `celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4`
3. Copy ALL the same environment variables from the API service

### 3e. Add Celery Beat service
1. Click **+ New** → **GitHub repo** → same repo
2. Settings:
   - **Start command:** `celery -A app.tasks.celery_app beat --loglevel=info`
3. Copy ALL the same environment variables

### 3f. Get API URL
1. Go to API service → **Settings > Networking** → **Generate Domain**
2. Copy the URL (e.g. `https://seo-tracker-production.up.railway.app`)

---

## Step 4: Vercel (Frontend)

1. Go to https://vercel.com → **Add New Project → Import Git Repository**
2. Select your repo
3. Configure:
   - **Root directory:** `frontend`
   - **Framework:** Next.js
4. **Environment Variables:**
   ```
   NEXT_PUBLIC_API_URL=https://seo-tracker-production.up.railway.app
   ```
5. Click **Deploy**

### Update CORS
Go back to Railway API service → Variables → update:
```
CORS_ORIGINS=["https://your-app.vercel.app"]
```

---

## Step 5: Verify

1. Open your Vercel URL → should see login page
2. Register an account
3. Create a project
4. Add keywords and competitors
5. Check Railway logs — agents should run on schedule
6. Check `/health` endpoint on Railway URL

---

## Architecture (deployed)

```
User → Vercel (Next.js frontend)
         ↓
       Railway API (FastAPI)
         ↓
       Supabase (PostgreSQL)
         ↓
       Railway Redis
         ↓
       Railway Celery Worker ──→ DataForSEO API
                              ──→ Playwright crawler
                              ──→ LLM APIs (ChatGPT, Perplexity, etc.)
                              ──→ Claude API (analysis)
                              ──→ Resend (email)
         ↓
       Railway Celery Beat (scheduler)
```

## Cost Estimate (at launch)

| Service | Cost |
|---------|------|
| Railway (API + Worker + Beat + Redis) | ~$10-20/mo |
| Supabase (Free → Pro) | $0-25/mo |
| Vercel (Hobby) | $0/mo |
| DataForSEO | ~$30-80/mo |
| Claude API | ~$20-50/mo |
| **Total** | **~$60-175/mo** |
