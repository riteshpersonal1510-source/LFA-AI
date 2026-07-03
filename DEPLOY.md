# AI Service Deployment Guide

## Render Configuration

### Build Command
```bash
cd ai-service && chmod +x build-improved.sh && ./build-improved.sh
```

### Start Command  
```bash
cd ai-service && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables
- `BROWSER_HEADLESS=true` (required for production)
- `BROWSER_MAX_POOL_SIZE=3` (default, adjust based on memory)
- `PLAYWRIGHT_BROWSERS_PATH=0` (use system path)
- `LOG_LEVEL=INFO`

## Critical Requirements

1. **Playwright Installation**: The build command MUST run `./build-improved.sh` which executes `playwright install chromium` (without `--with-deps` to avoid root escalation on Render).
2. **System Dependencies**: Render automatically provides required system packages for Chromium natively.
3. **Headless Mode**: Browser must run in headless mode in production
4. **Memory**: Each browser instance uses ~50-100MB RAM

## Verification

After deployment, test these endpoints:

1. **Health Check**: `GET /debug/browser`
   - Should return `"browser_launch_test": "success"`

2. **Scraper Test**: `POST /api/v1/scrape`
   - Should not return "BrowserPool: could not acquire" error

## Troubleshooting

### "Executable doesn't exist" Error
- Build command missing `./build-improved.sh` or `playwright install chromium`
- Clear build cache and redeploy

### "BrowserPool: could not acquire" Error  
- Check `/debug/browser` endpoint for specific error
- Verify Playwright installation in build logs

### Memory Issues
- Reduce `BROWSER_MAX_POOL_SIZE` to 1 or 2
- Check Render service memory limits