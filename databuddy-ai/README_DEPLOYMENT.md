# Quick Deployment Reference

## 🚀 Quick Start

### Backend (Render)
1. Push code to GitHub
2. Create Web Service on Render
3. Set environment variables (see `template.env`)
4. Deploy!

### Frontend (Vercel)
1. Import GitHub repo to Vercel
2. Set `NEXT_PUBLIC_API_URL` environment variable
3. Deploy!

## 📋 Required Environment Variables

### Backend (Render)
- `RUNSQL_URL` - Neon PostgreSQL connection string
- `GROQ_API_KEY` - Your Groq API key
- `CORS_ORIGINS` - Your Vercel frontend URL

### Frontend (Vercel)
- `NEXT_PUBLIC_API_URL` - Your Render backend URL

## 📁 Files Created

- `vercel.json` - Vercel deployment config
- `render.yaml` - Render deployment config
- `Procfile` - Render startup command
- `runtime.txt` - Python version for Render
- `template.env` - Complete environment variables template
- `backend/.env.template` - Backend-specific template
- `frontend/.env.local.template` - Frontend-specific template
- `DEPLOYMENT.md` - Detailed deployment guide

## 🔗 Links

- [Render Dashboard](https://dashboard.render.com/)
- [Vercel Dashboard](https://vercel.com/dashboard)
- [Neon PostgreSQL](https://neon.tech/)
- [Groq API](https://console.groq.com/)
