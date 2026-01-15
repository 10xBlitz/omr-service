# Quick Deployment Guide

## Deploy to Render (5 minutes)

### 1. Create GitHub Repository
```bash
cd /Users/withcenterdev/Desktop/projects/eduflow/omr-service
git init
git add .
git commit -m "Add OMR microservice with OpenCV"

# Create new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/eduflow-omr-service.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render
1. Go to https://render.com and sign up (free)
2. Click "New +" → "Web Service"
3. Click "Connect GitHub" and authorize
4. Select your `eduflow-omr-service` repository
5. Render auto-detects settings from `render.yaml`
6. Click "Create Web Service"
7. Wait 3-5 minutes for build

### 3. Get Service URL
After deployment, copy your service URL:
```
https://eduflow-omr-service.onrender.com
```

### 4. Add to Supabase Secrets
```bash
cd /Users/withcenterdev/Desktop/projects/eduflow
npx supabase secrets set OMR_SERVICE_URL="https://eduflow-omr-service.onrender.com"
```

### 5. Update Edge Function
The edge function code is already prepared. Just deploy:
```bash
npx supabase functions deploy process-omr-submission
```

## Test It

1. Upload an OMR sheet in your app
2. Check Supabase Function Logs
3. You should see:
   - "[OMR] Using Python CV service"
   - "CV-OMR detected X answers"
   - Much higher accuracy!

## Troubleshooting

**Cold starts**: First request after 15min inactivity takes 30-60s (free tier limitation)

**Solution**: Upgrade to Render paid tier ($7/month) for instant responses

**Check logs**: https://dashboard.render.com → Your Service → Logs

## Cost
- **Render Free Tier**: $0/month
- **Render Starter**: $7/month (no cold starts, faster)

For your use case, **free tier is perfect** to start!
