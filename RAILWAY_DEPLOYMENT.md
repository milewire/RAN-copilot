# Railway Deployment Guide

This guide explains how to deploy both the frontend and backend to Railway.

## Architecture

Railway will host:
1. **Backend Service** - FastAPI application
2. **Frontend Service** - Next.js application

## Prerequisites

- Railway account (sign up at https://railway.app)
- GitHub repository connected to Railway
- OpenAI API key (if using GPT-4o features)

## Deployment Steps

### 1. Deploy Backend

1. **Create New Project on Railway**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Add Backend Service**
   - Click "New Service" → "GitHub Repo"
   - Select your repository
   - **IMPORTANT**: In service settings, set **Root Directory** to `backend`
   - Railway will auto-detect it's a Python project from `backend/requirements.txt`

3. **Configure Backend Service**
   - **Root Directory**: `backend` (MUST be set in Railway dashboard)
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Python Version**: 3.11 (auto-detected from `runtime.txt` in backend/)

4. **Set Environment Variables** (in Railway dashboard):
   ```
   ALLOW_CLOUD=1
   OPENAI_API_KEY=your-api-key-here
   CORS_ORIGINS=https://your-frontend.railway.app,http://localhost:3000
   PORT=8000
   ```

5. **Deploy**
   - Railway will automatically build and deploy
   - Copy the generated URL (e.g., `https://your-backend.railway.app`)

### 2. Deploy Frontend

1. **Add Frontend Service**
   - In the same Railway project, click "New Service"
   - Select "GitHub Repo" again (same repo)
   - **IMPORTANT**: In service settings, set **Root Directory** to `frontend`
   - Railway will detect it's a Node.js project from `frontend/package.json`

2. **Configure Frontend Service**
   - **Root Directory**: `frontend` (MUST be set in Railway dashboard)
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`
   - **Node Version**: 18+ (auto-detected from `package.json`)

3. **Set Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NODE_ENV=production
   ```

4. **Deploy**
   - Railway will build and deploy
   - Copy the generated URL (e.g., `https://your-frontend.railway.app`)

### 3. Update CORS

After getting the frontend URL, update the backend's `CORS_ORIGINS` environment variable:
```
CORS_ORIGINS=https://your-frontend.railway.app,http://localhost:3000
```

Redeploy the backend service.

## Alternative: Single Service (Monorepo)

If you prefer a single service, you can:

1. Use Railway's monorepo support
2. Deploy backend and frontend as separate services in the same project
3. Use Railway's internal networking (services can communicate via service names)

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

