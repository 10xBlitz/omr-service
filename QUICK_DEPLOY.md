# Quick Deploy to Render using Docker Hub

## Step 1: Build and Push to Docker Hub (5 minutes)

```bash
cd /Users/withcenterdev/Desktop/projects/eduflow/omr-service

# Build the Docker image
docker build -t 10xblitz/eduflow-omr:latest .

# Login to Docker Hub (create account at https://hub.docker.com if needed)
docker login

# Push to Docker Hub
docker push 10xblitz/eduflow-omr:latest
```

Your image will be available at: `10xblitz/eduflow-omr:latest`

## Step 2: Deploy on Render from Docker Hub

### Method A: Using Render Dashboard (Easiest)

1. Go to https://render.com
2. Sign up/Login
3. Click "New +" → "Web Service"
4. Select "Deploy an existing image from a registry"
5. **Image URL**: `docker.io/10xblitz/eduflow-omr:latest`
6. **Name**: `eduflow-omr`
7. **Region**: Singapore
8. **Plan**: Free
9. **Port**: `5000` (important!)
10. Click "Create Web Service"

### Method B: Using render.yaml with Docker Hub

Update `render.yaml`:

```yaml
services:
  - type: web
    name: eduflow-omr-service
    env: docker
    region: singapore
    plan: free
    image:
      url: docker.io/10xblitz/eduflow-omr:latest
    envVars:
      - key: PORT
        value: 5000
```

Then:
1. Push updated render.yaml to GitHub
2. Connect repo on Render
3. Auto-deploys!

---

## OR Step 1 Alternative: Build on Render (Slower but simpler)

If you don't want to use Docker Hub:

1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect GitHub: `10xBlitz/omr-service`
4. **Environment**: Docker
5. Render builds from Dockerfile automatically
6. **Plan**: Free
7. Click "Create"

Render will build the Docker image from your Dockerfile.

---

## After Deployment

Get your service URL (e.g., `https://eduflow-omr-service.onrender.com`)

Then:

```bash
cd /Users/withcenterdev/Desktop/projects/eduflow

# Add service URL to Supabase
npx supabase secrets set OMR_SERVICE_URL="https://your-service.onrender.com"

# Update edge function
cp supabase/functions/process-omr-submission/index-with-cv.ts \
   supabase/functions/process-omr-submission/index.ts

# Deploy
npx supabase functions deploy process-omr-submission
```

Done! 🎉
