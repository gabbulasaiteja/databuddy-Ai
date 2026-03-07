# Deployment Guide

This guide covers deploying DataBuddy AI to Vercel (frontend) and Render (backend).

## Architecture

- **Frontend**: Next.js 15 app deployed on Vercel
- **Backend**: FastAPI app deployed on Render
- **Database**: Neon PostgreSQL (external service)

## Prerequisites

1. GitHub account with your repository
2. Vercel account (free tier available)
3. Render account (free tier available)
4. Neon PostgreSQL database (free tier available)
5. Groq API key (free tier available)

## Step 1: Deploy Backend to Render

### 1.1 Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository containing your code

### 1.2 Configure Render Service

**Basic Settings:**
- **Name**: `databuddy-ai-backend`
- **Region**: Choose closest to your users (e.g., Oregon)
- **Branch**: `main` (or your default branch)
- **Root Directory**: `databuddy-ai/backend`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Or use render.yaml:**
- Render will automatically detect `render.yaml` in your repository
- Make sure it's in the root or backend directory

### 1.3 Set Environment Variables in Render

Go to "Environment" tab and add:

**Required:**
```
RUNSQL_URL=postgresql+asyncpg://user:pass@host/db
GROQ_API_KEY=your_groq_api_key
CORS_ORIGINS=https://your-frontend.vercel.app
```

**Optional (with defaults):**
```
GROQ_MODEL=llama-3.3-70b-versatile
PORT=8000
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
QUERY_TIMEOUT=10.0
SELECT_LIMIT=50
AUTH_ENABLED=false
ERROR_TRACKING_ENABLED=true
ALERTING_ENABLED=true
```

### 1.4 Deploy

1. Click "Create Web Service"
2. Wait for build to complete (first build takes ~5 minutes)
3. Copy your service URL (e.g., `https://databuddy-ai-backend.onrender.com`)

## Step 2: Deploy Frontend to Vercel

### 2.1 Create Vercel Project

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. Select the repository

### 2.2 Configure Vercel Project

**Project Settings:**
- **Framework Preset**: Next.js
- **Root Directory**: `databuddy-ai/frontend`
- **Build Command**: `npm run build` (auto-detected)
- **Output Directory**: `.next` (auto-detected)
- **Install Command**: `npm install` (auto-detected)

**Or use vercel.json:**
- Vercel will automatically detect `vercel.json` in your repository

### 2.3 Set Environment Variables in Vercel

Go to "Settings" → "Environment Variables" and add:

**Required:**
```
NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
```

**Important Notes:**
- Replace `your-backend-url.onrender.com` with your actual Render backend URL
- The `NEXT_PUBLIC_` prefix makes this variable available in the browser
- Add this for all environments (Production, Preview, Development)

### 2.4 Update Backend CORS

1. Go back to Render dashboard
2. Update `CORS_ORIGINS` environment variable:
   ```
   CORS_ORIGINS=https://your-frontend.vercel.app,https://your-frontend-git-main.vercel.app
   ```
3. Redeploy backend service

### 2.5 Deploy

1. Click "Deploy"
2. Wait for build to complete (~2-3 minutes)
3. Your app will be live at `https://your-project.vercel.app`

## Step 3: Verify Deployment

### 3.1 Test Backend

```bash
# Health check
curl https://your-backend.onrender.com/health

# Schema endpoint
curl https://your-backend.onrender.com/api/schema
```

### 3.2 Test Frontend

1. Visit your Vercel URL
2. Check browser console for errors
3. Test database connection
4. Test AI query translation

## Troubleshooting

### Backend Issues

**Build Fails:**
- Check Python version (should be 3.9+)
- Verify `requirements.txt` is correct
- Check build logs in Render dashboard

**Service Crashes:**
- Check logs in Render dashboard
- Verify all required environment variables are set
- Ensure database connection string is correct

**CORS Errors:**
- Verify `CORS_ORIGINS` includes your Vercel frontend URL
- Check for trailing slashes in URLs
- Ensure backend is using HTTPS

### Frontend Issues

**API Connection Fails:**
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check browser console for CORS errors
- Ensure backend is running and accessible

**Build Fails:**
- Check Node.js version (should be 18+)
- Verify all dependencies are in `package.json`
- Check build logs in Vercel dashboard

## Environment Variables Reference

See `template.env` for complete list of all environment variables.

## Continuous Deployment

Both platforms support automatic deployments:
- **Render**: Auto-deploys on push to main branch
- **Vercel**: Auto-deploys on push to main branch

## Cost Estimation

**Free Tier Limits:**
- **Render**: 750 hours/month (enough for 24/7 free tier)
- **Vercel**: Unlimited (with some bandwidth limits)
- **Neon**: 0.5 GB storage, shared CPU
- **Groq**: Free tier available

**Total Cost**: $0/month on free tiers

## Security Checklist

- [ ] All API keys are in environment variables (not in code)
- [ ] CORS is properly configured
- [ ] Database connection uses SSL
- [ ] Authentication is enabled for production (optional)
- [ ] Rate limiting is configured
- [ ] Error tracking is enabled
- [ ] HTTPS is enforced (automatic on Vercel/Render)

## Support

For issues:
1. Check logs in respective dashboards
2. Verify environment variables
3. Test endpoints individually
4. Check GitHub issues
