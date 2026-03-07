# Environment variables for development and deployment

Use this as a checklist when setting up **local development** and when deploying to **Render** (PostgreSQL + Backend) and **Vercel** (Frontend).

---

## 1. PostgreSQL (Render)

Create a **PostgreSQL** instance in Render, then use its connection string.

| Variable | Where to set | Notes |
|----------|----------------|-------|
| **Internal Database URL** | Render Dashboard → your PostgreSQL service → **Info** tab → **Internal Database URL** | Use this for the **backend** (same Render account). Format: `postgresql://user:password@host/database` |

- You do **not** set env vars on the PostgreSQL service itself; you use its URL in the **backend** service.
- In the backend service, set either **DATABASE_URL** (paste Internal Database URL) or **RUNSQL_URL** (same URL; backend accepts both and converts to async driver).

---

## 2. Backend (Render)

Set these in **Render Dashboard → your Web Service (databuddy-ai-backend) → Environment**.

| Variable | Required | Example / value |
|----------|----------|------------------|
| `DATABASE_URL` | Yes (if not using RUNSQL_URL) | From Render Postgres: **Internal Database URL** (e.g. `postgresql://user:pass@host/db`) |
| `RUNSQL_URL` | Yes (if not using DATABASE_URL) | `postgresql+asyncpg://user:pass@host/db` (or leave unset and use DATABASE_URL) |
| `GROQ_API_KEY` | Yes | Your key from [Groq Console](https://console.groq.com/) |
| `CORS_ORIGINS` | Yes (production) | `https://your-app.vercel.app` (add your Vercel URL; comma-separated for multiple) |
| `PORT` | No | Render sets this automatically (e.g. `8000`) |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` (default) |
| `RATE_LIMIT_REQUESTS` | No | `10` |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` |
| `QUERY_TIMEOUT` | No | `10.0` |
| `SELECT_LIMIT` | No | `50` |
| `AUTH_ENABLED` | No | `false` |
| `API_KEYS` | No | Only if AUTH_ENABLED=true |
| `ERROR_TRACKING_ENABLED` | No | `true` |
| `ALERTING_ENABLED` | No | `true` |

**Quick steps:**

1. Create a **PostgreSQL** instance on Render.
2. Create a **Web Service** for the backend; connect your repo and use `render.yaml` (or set build/start commands and env manually).
3. In the backend service **Environment** tab:
   - Add **DATABASE_URL** → paste the **Internal Database URL** from your Postgres service (or add **RUNSQL_URL** with the same URL; the app accepts both).
   - Add **GROQ_API_KEY**.
   - Add **CORS_ORIGINS** = `https://<your-vercel-app>.vercel.app` (replace with your real Vercel URL after deploying the frontend).

---

## 3. Vercel (Frontend)

Set these in **Vercel Dashboard → your project → Settings → Environment Variables**.

| Variable | Required | Example / value |
|----------|----------|------------------|
| `NEXT_PUBLIC_API_URL` | Yes | Your Render backend URL (e.g. `https://databuddy-ai-backend.onrender.com`) |

**Quick steps:**

1. Import your repo as a Vercel project (e.g. root or `frontend` as root if repo is monorepo).
2. Add **NEXT_PUBLIC_API_URL** = `https://<your-render-backend>.onrender.com`.
3. Redeploy so the frontend uses the production API.

---

## Local development

- **Backend:** Copy `backend/.env.example` to `backend/.env` and set at least:
  - `RUNSQL_URL` or `DATABASE_URL` (e.g. local Postgres or Neon)
  - `GROQ_API_KEY`
  - `CORS_ORIGINS=http://localhost:3000`
- **Frontend:** Copy `frontend/.env.example` to `frontend/.env.local` and set:
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`

Do not commit `.env` or `.env.local`; they are listed in `.gitignore`.
