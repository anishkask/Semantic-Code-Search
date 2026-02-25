# Deployment Guide: Semantic Code Search

Step-by-step deployment for Railway (backend) and Vercel (frontend).

---

## Prerequisites

- Railway account: https://railway.app
- Vercel account: https://vercel.com
- Git repo with the project

---

## Part 1: Backend (Railway)

### Step 1.1: Commit chroma_db

Ensure the pre-built embeddings are in the repo:

```bash
# From project root
git add backend/vectordb/chroma_db/
git status   # Verify chroma_db is staged
git commit -m "Add pre-built ChromaDB embeddings for deployment"
```

If `chroma_db` was in `.gitignore`, remove it first:

```bash
# Edit .gitignore and remove any line matching chroma_db or vectordb/chroma_db
```

### Step 1.2: Deploy to Railway

1. Go to https://railway.app → **New Project**
2. Choose **Deploy from GitHub repo** (connect GitHub if needed)
3. Select your `semantic-code-search` repo
4. **Root Directory**: Set to `backend` (so Railway uses `backend/` as the build context)
5. Railway will detect the Dockerfile and build from it

**Or via Railway CLI:**

```bash
# Install Railway CLI: npm i -g @railway/cli
railway login
railway init
railway link   # Link to your project
railway up     # Deploy from backend/
```

### Step 1.3: Set Environment Variables (Railway)

In the Railway dashboard → your service → **Variables**:

| Variable         | Value        |
|------------------|--------------|
| `COLLECTION_NAME`| `flask_local`|
| `OPENAI_API_KEY` | `sk-your-key`|

(OPENAI_API_KEY is only needed if you use the OpenAI model; the default is `local`.)

### Step 1.4: Get the Backend URL

After deploy, Railway provides a URL like `https://your-app.up.railway.app`.

- Enable **Generate Domain** if needed
- Copy the public URL (e.g. `https://semantic-code-search-production.up.railway.app`)

---

## Part 2: Frontend (Vercel)

### Step 2.1: Update App.jsx (already done)

`frontend/src/App.jsx` uses:

```javascript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'
```

### Step 2.2: Local dev .env (already done)

`frontend/.env`:

```
VITE_API_URL=http://localhost:8001
```

### Step 2.3: Deploy to Vercel

1. Go to https://vercel.com → **Add New** → **Project**
2. Import your GitHub repo
3. **Root Directory**: Set to `frontend`
4. **Framework Preset**: Vite (auto-detected)
5. **Build Command**: `npm run build` (default)
6. **Output Directory**: `dist` (default)

### Step 2.4: Set Environment Variable (Vercel)

In Vercel → Project → **Settings** → **Environment Variables**:

| Name            | Value                              |
|-----------------|------------------------------------|
| `VITE_API_URL`  | `https://your-app.up.railway.app`  |

Use the Railway backend URL from Step 1.4. No trailing slash.

**Important**: Redeploy after adding the variable (Vercel bakes env vars at build time).

---

## Part 3: CORS

The FastAPI backend already has `allow_origins=["*"]`, so requests from your Vercel domain will work.

---

## Part 4: Verify

1. Open your Vercel URL (e.g. `https://semantic-code-search.vercel.app`)
2. Search for "how does Flask handle routing"
3. Results should load from the Railway backend

---

## Files Created

| File                    | Purpose                                      |
|-------------------------|----------------------------------------------|
| `backend/requirements.txt` | Pinned Python deps for Railway           |
| `backend/Dockerfile`    | Railway container build                      |
| `backend/.dockerignore` | Exclude unnecessary files from Docker build  |
| `frontend/.env`         | Local dev API URL                            |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 502 on Railway | Check logs; model load can take 60–90s on cold start |
| CORS errors | Confirm backend has `allow_origins=["*"]` |
| Empty results | Ensure `COLLECTION_NAME=flask_local` and chroma_db is committed |
| Frontend shows localhost | Rebuild on Vercel after setting `VITE_API_URL` |
