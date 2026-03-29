# SEO Competitor Intelligence Platform — Project Context

> Этот файл — единый источник правды по проекту.
> Обновляется после каждой рабочей сессии.
> Последнее обновление: 2026-03-29

---

## 1. Что строим

SaaS-платформа для мониторинга конкурентов в SEO + AI visibility (GEO).

Три основных модуля:
1. **SEO Rank Tracking** — ежедневная проверка позиций по ключевым словам (свой сайт + конкуренты) через DataForSEO
2. **Website Change Detection** — мониторинг изменений на страницах конкурентов (title, meta, контент, структура) через Playwright crawler
3. **GEO / AI Visibility** — трекинг упоминаний бренда в ответах AI-систем (ChatGPT, Claude, Perplexity, Gemini, DeepSeek) по модели Peec.ai

Плюс:
- Google Search Console + GA4 интеграция (реальные клики, трафик, конверсии)
- AI-анализ через Claude (корреляции: изменение на сайте → движение позиций → AI visibility)
- Smart-алерты (email, Slack, Telegram)

---

## 2. Ключевые решения

| Решение | Выбор | Почему |
|---------|-------|--------|
| Backend | FastAPI (Python 3.12) | Async, быстрый, Swagger из коробки |
| Frontend | Next.js 15 (будет) | App Router, Vercel deploy |
| Database | PostgreSQL через Supabase | Managed, Auth, RLS, free tier |
| Task queue | Celery + Redis | Beat scheduler для агентов |
| SERP API | DataForSEO | Batch mode $0.0006/запрос, самый выгодный |
| Change detection | Свой Playwright crawler | Максимальный контроль |
| AI analysis | Claude Sonnet API | Уже используем, структурированный output |
| GEO tracking | Multi-LLM: OpenAI + Perplexity + Claude + Gemini + DeepSeek | Perplexity — ключевой (нативные citations) |
| Email | Resend + React Email | 3000/мес бесплатно |
| Payments | Stripe | Subscriptions, webhooks |
| Deploy backend | Railway | 3 сервиса: web, worker, beat |
| Deploy frontend | Vercel | Edge, ISR |

---

## 3. Архитектура агентов (6 штук)

Все запускаются через Celery Beat по расписанию:

| # | Агент | Расписание | Зависимость |
|---|-------|-----------|-------------|
| 1 | 🎯 Rank Tracker | Daily 06:00 UTC | DataForSEO API |
| 2 | 🕵️ Change Detection | Daily 07:00 UTC | Playwright crawler |
| 3 | 📊 Google Data | Daily 07:30 UTC | GSC + GA4 API |
| 4 | 👁️ GEO Visibility | Weekly Mon 05:00 UTC | OpenAI, Perplexity, Claude, Gemini, DeepSeek API |
| 5 | 🧠 Analysis (Claude) | Daily 08:00 UTC | Данные от агентов 1-4 |
| 6 | 📢 Alert & Report | Daily 08:30 UTC | Данные от агента 5 |

---

## 4. Тарифные планы

| План | Цена | Проекты | Конкуренты | Keywords | GEO промпты |
|------|------|---------|------------|----------|-------------|
| Free | $0 | 1 | 2 | 20 | — |
| Starter | $29 | 1 | 3 | 50 | — |
| Pro | $99 | 5 | 10 | 300 | 50 (3 LLM) |
| Agency | $249 | 20 | 50 | 2000 | 200 (5 LLM) |

---

## 5. Модели базы данных

### Core
- `users` — auth, plan, Stripe, Google tokens
- `projects` — домен пользователя, GSC/GA4 property IDs, гео/язык настройки
- `competitors` — конкуренты привязанные к проекту
- `keywords` — ключевые слова для трекинга
- `rank_history` — ежедневные снэпшоты позиций (keyword × domain × device × date), GSC-данные
- `tracked_pages` — URL-ы конкурентов для мониторинга
- `page_snapshots` — снэпшот SEO-элементов страницы
- `change_log` — обнаруженные изменения между снэпшотами
- `agent_runs` — логи выполнения каждого агента

### GEO
- `llm_prompts` — библиотека промптов для AI visibility tracking
- `llm_responses` — полные ответы от каждой LLM-платформы (+ citations, sources)
- `llm_mentions` — обнаруженные упоминания бренда/конкурентов в ответах (mention, citation, position, sentiment)
- `geo_visibility_snapshots` — еженедельные агрегированные метрики (mention_rate, citation_rate, share_of_voice)

---

## 6. Структура файлов проекта

```
seo-tracker/
├── app/
│   ├── api/v1/
│   │   ├── __init__.py          # Router aggregator
│   │   ├── auth.py              # Register, login, refresh, me
│   │   ├── projects.py          # Project CRUD
│   │   ├── competitors.py       # Competitors + Keywords CRUD
│   │   └── geo.py               # GEO prompts, visibility data
│   ├── core/
│   │   ├── config.py            # Pydantic settings from .env
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   └── security.py          # JWT, password hashing, get_current_user
│   ├── models/
│   │   ├── __init__.py          # All model imports
│   │   ├── user.py              # User + PlanTier enum
│   │   ├── project.py           # Project
│   │   ├── competitor.py        # Competitor
│   │   ├── keyword.py           # Keyword + RankHistory
│   │   ├── page.py              # TrackedPage + PageSnapshot + ChangeLog
│   │   ├── agent_run.py         # AgentRun + AgentType + RunStatus
│   │   └── geo.py               # LLMPrompt + LLMResponse + LLMMention + GEOSnapshot
│   ├── schemas/
│   │   ├── auth.py              # Auth request/response schemas
│   │   └── project.py           # Project/Competitor/Keyword schemas
│   ├── services/
│   │   ├── dataforseo.py        # DataForSEO SERP API client (batch + live)
│   │   ├── change_detection.py  # Playwright crawler + diff engine
│   │   └── geo_visibility.py    # Multi-LLM query engine + mention detection
│   ├── tasks/
│   │   ├── __init__.py          # Celery app + Beat schedule
│   │   └── agents.py            # 6 agent task stubs
│   ├── agents/                  # (пока пустая — будет логика агентов)
│   └── main.py                  # FastAPI app entry point
├── migrations/
│   ├── env.py                   # Alembic async env
│   └── script.py.mako           # Migration template
├── tests/
├── docker-compose.yml           # Postgres + Redis + API + Celery worker + beat
├── Dockerfile
├── Procfile                     # Railway multi-service
├── railway.toml
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 7. Прогресс

### ✅ Сделано
- [x] Фаза 1: Backend фундамент (FastAPI + DB models + Auth + CRUD API)
- [x] Фаза 1: Docker Compose (Postgres + Redis + API + Celery)
- [x] Фаза 1: Alembic миграции (async setup)
- [x] Фаза 1: Railway + Vercel deploy конфиги
- [x] Фаза 2: DataForSEO сервис (batch + live)
- [x] Фаза 2: Change Detection сервис (Playwright + BeautifulSoup + difflib)
- [x] GEO: Multi-LLM query engine (5 платформ)
- [x] GEO: Brand mention detection + scoring + share of voice
- [x] GEO: API endpoints (prompts CRUD, visibility snapshots)
- [x] GEO: DB models (llm_prompts, llm_responses, llm_mentions, geo_snapshots)
- [x] Celery Beat schedule для всех 6 агентов
- [x] Интерактивный HTML план (7 фаз, 5 вкладок)
- [x] **Agent Logic: Rank Tracker** — полная реализация (DB → DataForSEO → rank_history → anomaly flags)
- [x] **Agent Logic: Change Detection** — полная реализация (DB → Playwright crawl → diff → change_log)
- [x] **Agent Logic: GEO Visibility** — полная реализация (DB → 5 LLM APIs → mentions → snapshots)
- [x] **Agent Logic: Analysis (Claude)** — полная реализация (gather all data → Claude prompt → structured JSON)
- [x] **Agent Logic: Alert & Report** — полная реализация (critical alerts + daily digest email via Resend)
- [x] Agent API endpoints (manual trigger + run history)
- [x] Sync DB sessions для Celery workers
- [x] CONTEXT.md + SESSION_LOG.md
- [x] **Frontend: Next.js 15 app** — full project setup (TS, Tailwind, custom design tokens)
- [x] **Frontend: API client** — typed HTTP wrapper with JWT refresh for all endpoints
- [x] **Frontend: Auth pages** — login + register with error handling
- [x] **Frontend: Dashboard overview** — project list, stats, create modal
- [x] **Frontend: Keywords page** — table with sort, position/change badges, bulk import, run trigger
- [x] **Frontend: Competitors page** — card grid, favicon, add/delete
- [x] **Frontend: Changes page** — timeline with severity filters, expandable diffs, AI summary
- [x] **Frontend: GEO AI Visibility** — platform cards with metrics, sentiment bars, prompt management
- [x] **Frontend: Sidebar + project layout** — navigation with project context bar
- [x] **Frontend: Recharts** — RankChart (position trend), VisibilityChart (GEO trends), DistributionChart (SoV bars)
- [x] **Backend: Rank History API** — /history, /chart, /summary endpoints for chart data
- [x] **Backend: Changes API** — /changes endpoint for timeline view
- [x] **DEPLOY.md** — step-by-step Railway + Vercel deploy guide

### 🔲 Следующие шаги
- [ ] Google Search Console + GA4 сервис
- [ ] Stripe интеграция
- [ ] Тесты
- [ ] Деплой на Railway + Vercel

---

## 8. API Endpoints (текущие)

```
Auth:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
  GET  /api/v1/auth/me

Projects:
  GET    /api/v1/projects
  POST   /api/v1/projects
  GET    /api/v1/projects/:id
  PATCH  /api/v1/projects/:id
  DELETE /api/v1/projects/:id

Competitors:
  GET    /api/v1/projects/:id/competitors
  POST   /api/v1/projects/:id/competitors
  DELETE /api/v1/competitors/:id

Keywords:
  GET    /api/v1/projects/:id/keywords
  POST   /api/v1/projects/:id/keywords
  POST   /api/v1/projects/:id/keywords/bulk
  DELETE /api/v1/keywords/:id

GEO:
  GET    /api/v1/geo/projects/:id/prompts
  POST   /api/v1/geo/projects/:id/prompts
  POST   /api/v1/geo/projects/:id/prompts/bulk
  DELETE /api/v1/geo/prompts/:id
  GET    /api/v1/geo/projects/:id/visibility

Agents:
  POST   /api/v1/agents/projects/:id/run-all
  POST   /api/v1/agents/projects/:id/run/:agent_type
  GET    /api/v1/agents/projects/:id/runs

Data:
  GET    /api/v1/data/projects/:id/rank-history/:keyword_id
  GET    /api/v1/data/projects/:id/changes
  GET    /api/v1/data/projects/:id/stats
```

---

## 9. Бюджет (ежемесячно)

| Этап | Инфра | API | Итого |
|------|-------|-----|-------|
| MVP (до 50 юзеров) | ~$50 | ~$100 | ~$150/мес |
| Growth (100-500 юзеров) | ~$200 | ~$500 | ~$700/мес |
| Target: 200 платящих @ $60 avg | — | — | MRR $12K, margin ~94% |
