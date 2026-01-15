# Docker Deployment Guide

## Option 1: Render (Easiest, Free)

### Deploy with Docker on Render

1. **Push to GitHub** (already done ✓)

2. **Go to Render**: https://render.com

3. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect GitHub repo: `10xBlitz/omr-service`
   - **Environment**: Docker
   - **Plan**: Free
   - Click "Create Web Service"

4. **Render auto-detects Dockerfile** and builds

5. **Get your URL**: `https://your-service.onrender.com`

---

## Option 2: Railway (Free $5/month credit)

### Deploy to Railway

1. **Go to Railway**: https://railway.app

2. **New Project** → **Deploy from GitHub**

3. **Select** `10xBlitz/omr-service`

4. **Railway auto-detects Dockerfile**

5. **Generate domain** in Settings → Networking

6. **Get URL**: `https://your-service.up.railway.app`

**Note**: Railway gives you $5/month free credit (enough for ~500 hours/month)

---

## Option 3: Google Cloud Run (Best Free Tier)

### Deploy to Cloud Run (Most Generous Free Tier)

**Free Tier**: 2 million requests/month, 360,000 GB-seconds/month

1. **Build and push to Docker Hub**:
```bash
cd /Users/withcenterdev/Desktop/projects/eduflow/omr-service

# Build image
docker build -t 10xblitz/eduflow-omr:latest .

# Login to Docker Hub
docker login

# Push to Docker Hub
docker push 10xblitz/eduflow-omr:latest
```

2. **Deploy to Cloud Run**:
```bash
# Install gcloud CLI (if not installed)
# https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login

# Deploy
gcloud run deploy eduflow-omr \
  --image 10xblitz/eduflow-omr:latest \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --port 5000 \
  --memory 512Mi
```

3. **Get URL**: `https://eduflow-omr-xxxxx.a.run.app`

---

## Option 4: Fly.io (Free Tier)

### Deploy to Fly.io

1. **Install flyctl**:
```bash
brew install flyctl
# or
curl -L https://fly.io/install.sh | sh
```

2. **Login**:
```bash
flyctl auth login
```

3. **Deploy**:
```bash
cd /Users/withcenterdev/Desktop/projects/eduflow/omr-service

# Launch (creates fly.toml)
flyctl launch

# Choose:
# - App name: eduflow-omr
# - Region: Singapore (sin)
# - No PostgreSQL
# - No Redis

# Deploy
flyctl deploy
```

4. **Get URL**: `https://eduflow-omr.fly.dev`

---

## Local Testing

### Test Docker locally before deploying:

```bash
cd /Users/withcenterdev/Desktop/projects/eduflow/omr-service

# Build image
docker build -t eduflow-omr .

# Run container
docker run -p 5000:5000 eduflow-omr

# Test health endpoint
curl http://localhost:5000/health

# Test OMR processing
curl -X POST http://localhost:5000/process-omr \
  -H "Content-Type: application/json" \
  -d '{
    "imageUrl": "YOUR_OMR_IMAGE_URL",
    "numberOfQuestions": 45
  }'
```

---

## Recommended for You: **Render**

**Why Render?**
- ✅ Simplest setup (just connect GitHub)
- ✅ Auto-deploys on git push
- ✅ Free tier (no credit card needed)
- ✅ Auto-detects Dockerfile
- ✅ Built-in SSL
- ⚠️ Only downside: Cold starts (30-60s after 15min inactivity)

**For production** (no cold starts): Upgrade to Render Starter ($7/month)

---

## Comparison

| Platform | Free Tier | Cold Starts | Ease | Best For |
|----------|-----------|-------------|------|----------|
| **Render** | ✅ Yes | Yes (15min) | ⭐⭐⭐⭐⭐ | Quick start |
| **Railway** | $5 credit/mo | No | ⭐⭐⭐⭐ | Dev projects |
| **Cloud Run** | 2M req/mo | Yes | ⭐⭐⭐ | Production |
| **Fly.io** | Limited | Minimal | ⭐⭐⭐⭐ | Global apps |

---

## After Deployment

Once deployed, add the URL to Supabase:

```bash
cd /Users/withcenterdev/Desktop/projects/eduflow
npx supabase secrets set OMR_SERVICE_URL="https://your-service-url.com"
```
