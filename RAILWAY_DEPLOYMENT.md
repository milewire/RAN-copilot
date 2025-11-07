# Railway Deployment Guide

This guide explains how to deploy both the frontend and backend to Railway.

## Architecture

Railway requires **TWO SEPARATE SERVICES** in the same project:

1. **Backend Service** - FastAPI application (Root Directory: `backend`)
2. **Frontend Service** - Next.js application (Root Directory: `frontend`)

**Important**: Each service is completely independent with its own:
- Root directory setting
- Build process
- Environment variables
- Public URL/domain

## Prerequisites

- Railway account (sign up at https://railway.app)
- GitHub repository connected to Railway
- OpenAI API key (if using GPT-4o features)

## Deployment Steps

### Important: Two Separate Services Required

Railway requires **two separate services** - one for backend, one for frontend. Each service has its own root directory setting.

### 1. Create Railway Project

1. **Create New Project on Railway**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository: `milewire/pLTE-band41-RCA`

### 2. Deploy Backend Service

1. **Add Backend Service**
   - In your Railway project, click "New Service"
   - Select "GitHub Repo"
   - Choose the same repository
   - **IMPORTANT**: Railway will create a new service

2. **Configure Backend Service Root Directory**
   - Click on the newly created service
   - Go to **Settings** tab
   - Scroll to **Service** section
   - Find **Root Directory** field
   - Set it to: `backend` (without quotes)
   - Click **Save**

3. **Railway will auto-detect:**
   - Python project (from `backend/requirements.txt`)
   - Python version 3.11 (from `backend/runtime.txt`)
   - Start command from `backend/railway.json`

4. **Set Environment Variables** (in Railway dashboard → Variables tab):
   ```
   ALLOW_CLOUD=1
   OPENAI_API_KEY=your-api-key-here
   CORS_ORIGINS=http://localhost:3000
   ```
   (You'll update CORS_ORIGINS after frontend is deployed - Railway sets PORT automatically)

5. **Deploy**
   - Railway will automatically build and deploy
   - Copy the generated URL (e.g., `https://your-backend.railway.app`)

### 3. Deploy Frontend Service

1. **Add Frontend Service** (in the SAME Railway project)
   - Click "New Service" again
   - Select "GitHub Repo"
   - Choose the same repository
   - **This creates a SECOND service** (separate from backend)

2. **Configure Frontend Service Root Directory**
   - Click on the newly created frontend service
   - Go to **Settings** tab
   - Scroll to **Service** section
   - Find **Root Directory** field
   - Set it to: `frontend` (without quotes)
   - Click **Save**

3. **Railway will auto-detect:**
   - Node.js project (from `frontend/package.json`)
   - Build command: `npm install && npm run build`
   - Start command from `frontend/railway.json`

4. **Set Environment Variables** (in Railway dashboard → Variables tab):
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NODE_ENV=production
   ```
   (Replace with your actual backend URL from step 2)

5. **Deploy**
   - Railway will build and deploy
   - Copy the generated URL (e.g., `https://your-frontend.railway.app`)

### 4. Connect Frontend to Backend

1. **Get Backend URL**
   - In Railway dashboard, click on your backend service
   - Go to **Settings** → **Networking**
   - Copy the **Public Domain** URL (e.g., `https://your-backend.railway.app`)

2. **Set Frontend Environment Variable**
   - Click on your frontend service
   - Go to **Variables** tab
   - Add/Update variable:
     ```
     NEXT_PUBLIC_API_URL=https://your-backend.railway.app
     NODE_ENV=production
     ```
   - Replace `https://your-backend.railway.app` with your actual backend URL

3. **Update Backend CORS**
   - Get your frontend URL (from frontend service → Settings → Networking)
   - Go to backend service → **Variables** tab
   - Update `CORS_ORIGINS`:
     ```
     CORS_ORIGINS=https://your-frontend.railway.app,http://localhost:3000
     ```
   - Replace with your actual frontend URL

4. **Redeploy Services**
   - Both services will automatically redeploy when you save environment variables
   - Or manually trigger redeploy from the **Deployments** tab

## Railway Project Structure

Your Railway project will have **two services**:

```
Railway Project: pLTE-band41-RCA
├── Service 1: Backend
│   ├── Root Directory: backend
│   ├── URL: https://your-backend.railway.app
│   └── Environment: Python 3.11
│
└── Service 2: Frontend
    ├── Root Directory: frontend
    ├── URL: https://your-frontend.railway.app
    └── Environment: Node.js 18+
```

Both services are in the same project but are completely separate deployments with their own:
- Root directories
- Environment variables
- URLs/domains
- Build processes

## Environment Variables Summary

### Backend Service
- `ALLOW_CLOUD` - Set to `1` to enable GPT-4o
- `OPENAI_API_KEY` - Your OpenAI API key
- `CORS_ORIGINS` - Comma-separated list of allowed origins
- `PORT` - Railway sets this automatically (use `$PORT`)

### Frontend Service
- `NEXT_PUBLIC_API_URL` - Your backend Railway URL
- `NODE_ENV` - Set to `production`

## File Storage Considerations

⚠️ **Important**: Railway uses ephemeral storage. Files uploaded to `backend/uploads/` will be lost when the service restarts. This is fine for this application since files are processed immediately and results are returned to the client.

If you need persistent storage, consider:
- Railway Volumes (for persistent file storage)
- External storage (S3, Cloudflare R2, etc.)

## Custom Domain

Railway provides free `.railway.app` domains. You can also add custom domains:
1. Go to service settings
2. Click "Generate Domain" or "Add Custom Domain"
3. Update `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL` accordingly

## Monitoring

Railway provides:
- Logs for both services
- Metrics and usage stats
- Automatic deployments on git push

## Troubleshooting

### Backend won't start
- Check logs in Railway dashboard
- Verify Python version (3.11)
- Ensure `requirements.txt` is in `backend/` directory
- Check that `PORT` environment variable is set

### Frontend can't connect to backend
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS settings in backend
- Ensure backend URL is accessible (not internal)

### CORS errors
- Update `CORS_ORIGINS` to include your frontend URL
- Ensure no trailing slashes in URLs
- Redeploy backend after changing CORS settings

## Cost

Railway offers:
- **Free tier**: $5 credit/month
- **Hobby plan**: $5/month + usage
- Both services should fit comfortably in the free tier for development/demo

## Next Steps

1. Deploy backend first
2. Get backend URL
3. Deploy frontend with backend URL
4. Update CORS if needed
5. Test the application!

