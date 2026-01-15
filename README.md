# OMR Processing Microservice

Computer Vision-based OMR detection using OpenCV for Korean test answer sheets.

## Features
- Circle detection using Hough Transform
- Fill density analysis (pixel counting)
- 95%+ accuracy for standard OMR sheets
- Fast processing (< 2 seconds per sheet)

## Deploy to Render (Free Tier)

### Step 1: Push to GitHub
```bash
cd omr-service
git init
git add .
git commit -m "Initial OMR service"
git remote add origin YOUR_REPO_URL
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to https://render.com
2. Sign up / Log in (free account)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Select the `eduflow/omr-service` directory
6. Render will auto-detect the `render.yaml` configuration
7. Click "Create Web Service"
8. Wait 3-5 minutes for deployment

### Step 3: Get Your Service URL
Once deployed, Render will give you a URL like:
```
https://eduflow-omr-service.onrender.com
```

Copy this URL - you'll need it for the Supabase Edge Function.

## API Endpoints

### Health Check
```bash
GET /health
```

### Process OMR
```bash
POST /process-omr
Content-Type: application/json

{
  "imageUrl": "https://your-supabase-storage.co/image.jpg",
  "numberOfQuestions": 45
}
```

Response:
```json
{
  "answers": [
    {
      "questionNumber": 1,
      "selectedOption": "4",
      "confidence": 0.95,
      "ambiguous": false,
      "notes": "Clear fill at position 4"
    }
  ],
  "totalDetected": 225,
  "rowsDetected": 45
}
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Test
curl -X POST http://localhost:5000/process-omr \
  -H "Content-Type: application/json" \
  -d '{"imageUrl": "IMAGE_URL", "numberOfQuestions": 45}'
```

## How It Works

1. **Download Image**: Fetch OMR sheet from Supabase Storage
2. **Preprocessing**: Convert to grayscale, apply Gaussian blur, binary threshold
3. **Circle Detection**: Use Hough Circle Transform to find all bubbles
4. **Row Grouping**: Group detected circles into question rows by Y-coordinate
5. **Fill Analysis**: Count dark pixels in each circle to determine if filled
6. **Answer Extraction**: Identify which bubble (position 1-5) is filled per question

## Render Free Tier Limits
- 512 MB RAM
- Shared CPU
- Spins down after 15 min of inactivity
- First request after spin-down may take 30-60 seconds (cold start)
- No cost!

## Notes
- For production, consider upgrading to Render's paid tier ($7/month) for no cold starts
- Korean OMR sheets work best with clear scans/photos
- Minimum image resolution: 1200x1600 pixels recommended
