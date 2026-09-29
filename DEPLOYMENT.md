# AERIX Production Cloud Deployment Guide

A concise, step-by-step guide to deploying the **AERIX Sovereign Airfare Price Index** to cloud infrastructure:
- **Frontend**: Vercel (React 19 / Vite)
- **Backend**: Render (FastAPI Web Service)
- **Database**: Neon (Serverless PostgreSQL)

---

## Prerequisites

- [GitHub](https://github.com/) repository containing the codebase.
- Accounts on:
  - [Neon Console](https://console.neon.tech/)
  - [Render Dashboard](https://dashboard.render.com/)
  - [Vercel Dashboard](https://vercel.com/)

---

## Step A: Configure Neon PostgreSQL

1. Open your [Neon Console](https://console.neon.tech/) and navigate to your active database project (or create a new PostgreSQL 16 project).
2. On the **Dashboard**, locate your connection details:
   - Copy the **Pooled Connection String** (`postgresql://...` with `-pooler` subdomain).
3. Prepare two environment connection strings:
   - **`DATABASE_URL_SYNC`**:  
     `postgresql://<user>:<password>@<neon-host>.neon.tech/neondb?sslmode=require`
   - **`DATABASE_URL`** (Async driver for scraper):  
     `postgresql+asyncpg://<user>:<password>@<neon-host>.neon.tech/neondb?sslmode=require`
4. If migrating from scratch, execute schema migrations:
   ```bash
   alembic upgrade head
   ```
   *(Note: The active Neon DB already contains 12,212 validated production observations).*

---

## Step B: Deploy FastAPI Backend to Render

1. Log in to [Render Dashboard](https://dashboard.render.com/) and click **New +** $\to$ **Blueprint** (or connect via `render.yaml`).
   - Alternatively, choose **New +** $\to$ **Web Service** manually.
2. If configuring manually:
   - **Name**: `aerix-api`
   - **Region**: Singapore / Oregon
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn apps.api.src.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
3. In the **Environment Variables** tab, add:
   ```env
   ENVIRONMENT=production
   PYTHONPATH=.
   DATABASE_URL_SYNC=postgresql://<user>:<password>@<neon-host>.neon.tech/neondb?sslmode=require
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@<neon-host>.neon.tech/neondb?sslmode=require
   FRONTEND_ORIGIN=http://localhost:5173
   ```
   *(We will update `FRONTEND_ORIGIN` with your Vercel URL in Step E).*
4. Click **Create Web Service**. Wait for the build and deployment to finish.
5. Copy your public service URL:  
   `https://aerix-api.onrender.com`

---

## Step C: Deploy React Frontend to Vercel

1. Log in to [Vercel](https://vercel.com/) and click **Add New...** $\to$ **Project**.
2. Select your `SIH2026` Git repository.
3. In **Project Configuration**:
   - **Root Directory**: Click `Edit` and select **`web`**.
   - **Framework Preset**: `Vite` (automatically detected).
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   ```env
   VITE_API_BASE_URL=https://aerix-api.onrender.com
   ```
   *(Replace with your actual Render API URL from Step B).*
5. Click **Deploy**. Vercel will build the SPA in ~30 seconds.
6. Copy your deployed frontend URL:  
   `https://your-aerix-app.vercel.app`

---

## Step D: Connect Frontend to API (CORS Interlock)

To allow the Vercel frontend to call your Render FastAPI backend securely without CORS blocks:

1. Return to the **Render Dashboard** $\to$ `aerix-api` $\to$ **Environment**.
2. Update the `FRONTEND_ORIGIN` variable with your Vercel domain:
   ```env
   FRONTEND_ORIGIN=https://your-aerix-app.vercel.app
   ```
   *(Multiple domains can be separated with a comma, e.g. `https://your-aerix-app.vercel.app,http://localhost:5173`).*
3. Save changes. Render will automatically redeploy the backend with the new CORS origin policy active.

---

## Step F: Run Health Checks & Post-Deployment Verification

1. **Verify Backend Health**:
   Open in your browser:
   ```
   https://aerix-api.onrender.com/health
   ```
   Expected response:
   ```json
   {
     "status": "HEALTHY",
     "data_status": "REAL_PRODUCTION_SURVEILLANCE",
     "database": {
       "type": "Neon PostgreSQL (Hosted)",
       "status": "CONNECTED",
       "fare_observations_count": 12212
     },
     "redis": {
       "type": "None",
       "status": "NOT_CONFIGURED"
     }
   }
   ```

2. **Verify Critical Data Endpoints**:
   - `https://aerix-api.onrender.com/api/v1/coverage` $\to$ `{"coverage_percent": 100.0, ...}`
   - `https://aerix-api.onrender.com/api/v1/matrix` $\to$ 360 cells across 60 routes
   - `https://aerix-api.onrender.com/api/v1/backtest` $\to$ Econometric validation summary

3. **Verify Dashboard Interaction**:
   Open `https://your-aerix-app.vercel.app` in your browser. Verify:
   - Overview metrics populate without CORS console errors.
   - Lead-time booking curves render for Top routes (DEL–BOM, DEL–BLR, BOM–BLR).
   - Route basket search & filter works across all 60 DGCA domestic sectors.
