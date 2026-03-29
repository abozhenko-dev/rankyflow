# SEO Competitor Intelligence Platform

Full-stack SaaS for competitor SEO monitoring, rank tracking, website change detection, AI analysis, and GEO/AI Visibility tracking (à la Peec.ai).

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Next.js 15  │────▶│  FastAPI     │────▶│ PostgreSQL  │
│  (Vercel)    │     │  (Railway)   │     │ (Supabase)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │ Celery +    │
                    │ Redis       │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │ Rank      │   │ Change    │   │ GEO       │
    │ Tracker   │   │ Detection │   │ Visibility│
    │ Agent     │   │ Agent     │   │ Agent     │
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │                │                │
    ┌─────▼────────────────▼────────────────▼─────┐
    │           Analysis Agent (Claude AI)         │
    └──────────────────┬──────────────────────────┘
                       │
               ┌───────▼───────┐
               │ Alert & Report│
               │ Agent         │
               └───────────────┘
```

## 6 Agents

| Agent | Schedule | Data Source |
|-------|----------|-------------|
| 🎯 Rank Tracker | Daily 06:00 | DataForSEO API |
| 🕵️ Change Detection | Daily 07:00 | Playwright crawler |
| 📊 Google Data | Daily 07:30 | GSC + GA4 API |
| 👁️ GEO Visibility | Weekly Mon 05:00 | ChatGPT, Claude, Perplexity, Gemini, DeepSeek |
| 🧠 Analysis | Daily 08:00 | Claude API |
| 📢 Alert & Report | Daily 08:30 | Resend + Slack + Telegram |

## Quick Start (Docker)

```bash
# 1. Clone & configure
cp .env.example .env
# Edit .env with your API keys

# 2. Start all services
docker compose up -d

# 3. Run migrations
docker compose exec api alembic upgrade head

# 4. Open API docs
open http://localhost:8000/docs
```

## Quick Start (Local)

```bash
# 1. Python env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Start PostgreSQL & Redis (or use Supabase + Upstash)
# Update .env with connection strings

# 3. Migrations
alembic upgrade head

# 4. Run API
uvicorn app.main:app --reload

# 5. Run Celery worker + beat (separate terminals)
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info
```

## Deploy to Railway

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login & init
railway login
railway init

# 3. Add services: PostgreSQL + Redis from Railway marketplace
# 4. Set environment variables in Railway dashboard
# 5. Deploy
railway up
```

Create 3 Railway services from the same repo:
- **web** → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **worker** → `celery -A app.tasks.celery_app worker --loglevel=info`
- **beat** → `celery -A app.tasks.celery_app beat --loglevel=info`

## API Endpoints (Phase 1)

### Auth
- `POST /api/v1/auth/register` — create account
- `POST /api/v1/auth/login` — get JWT tokens
- `POST /api/v1/auth/refresh` — refresh access token
- `GET  /api/v1/auth/me` — current user

### Projects
- `GET    /api/v1/projects` — list user projects
- `POST   /api/v1/projects` — create project
- `GET    /api/v1/projects/:id` — get project
- `PATCH  /api/v1/projects/:id` — update project
- `DELETE /api/v1/projects/:id` — delete project

### Competitors
- `GET    /api/v1/projects/:id/competitors` — list competitors
- `POST   /api/v1/projects/:id/competitors` — add competitor
- `DELETE /api/v1/competitors/:id` — remove competitor

### Keywords
- `GET    /api/v1/projects/:id/keywords` — list keywords
- `POST   /api/v1/projects/:id/keywords` — add keyword
- `POST   /api/v1/projects/:id/keywords/bulk` — bulk import
- `DELETE /api/v1/keywords/:id` — remove keyword

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 (Supabase) |
| Queue | Celery + Redis |
| AI | Anthropic Claude API |
| SERP | DataForSEO API |
| GEO | OpenAI, Perplexity, Gemini, DeepSeek APIs |
| Scraping | Playwright, BeautifulSoup |
| Email | Resend + React Email |
| Payments | Stripe |
| Hosting | Vercel (front) + Railway (back) |

## License

Proprietary — All rights reserved.
