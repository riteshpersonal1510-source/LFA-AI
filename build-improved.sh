#!/bin/bash
set -e  # Exit immediately if any command fails

echo "======================================"
echo "🚀 AI Service Build Script (Separate Repo)"
echo "======================================"

# Debug environment
echo "📍 Working directory: $(pwd)"
echo "📍 Python version: $(python --version 2>&1)"
echo "📍 Pip version: $(pip --version 2>&1)"
echo "📍 Directory contents:"
ls -la | head -10

# Step 1: Upgrade pip and install dependencies
echo "📦 Installing Python dependencies..."
python -m pip install --upgrade pip

# Install requirements (assuming requirements.txt is at repo root for AI service)
if [ -f "requirements.txt" ]; then
    echo "📦 Installing from requirements.txt..."
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found in $(pwd)"
    echo "Available files:"
    ls -la
    exit 1
fi

echo "✅ Python dependencies installed"

# Step 2: Install Playwright browsers
echo "🎭 Installing Playwright browsers..."

# Set Playwright cache directory for Render
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright
echo "📍 PLAYWRIGHT_BROWSERS_PATH set to: $PLAYWRIGHT_BROWSERS_PATH"

# Verify Playwright is installed
python -c "import playwright; print(f'Playwright {playwright.__version__} installed')" || {
    echo "❌ Playwright not properly installed"
    exit 1
}

# Install Chromium without system dependencies (Render does not allow sudo/su)
echo "🎭 Installing Chromium browser..."
playwright install chromium 2>&1 || {
    echo "❌ Chromium installation failed completely"
    exit 1
}

# Step 3: Comprehensive verification
echo "🔍 Verifying Chromium installation..."
python3 -c """
import os, sys
from playwright.sync_api import sync_playwright

print('🔍 Starting Chromium verification...')

try:
    p = sync_playwright().start()
    chromium_path = p.chromium.executable_path
    print(f'📍 Chromium path: {chromium_path}')
    
    if not os.path.exists(chromium_path):
        print(f'❌ Chromium executable missing at: {chromium_path}')
        
        # Debug: List Playwright cache
        cache_dir = '/opt/render/.cache/ms-playwright'
        if os.path.exists(cache_dir):
            print('📂 Playwright cache contents:')
            for item in os.listdir(cache_dir):
                item_path = os.path.join(cache_dir, item)
                if os.path.isdir(item_path):
                    print(f'  📁 {item}/')
                    try:
                        for subitem in os.listdir(item_path)[:5]:
                            print(f'    📄 {subitem}')
                    except: pass
                else:
                    print(f'  📄 {item}')
        sys.exit(1)
    
    # Test executable permissions
    if not os.access(chromium_path, os.X_OK):
        print(f'❌ Chromium not executable: {chromium_path}')
        sys.exit(1)
    
    print('✅ Chromium executable found and has correct permissions')
    
    # Test launch capability
    print('🚀 Testing Chromium launch...')
    browser = p.chromium.launch(headless=True)
    print('✅ Chromium launched successfully')
    browser.close()
    print('✅ Chromium closed successfully')
    p.stop()
    
    print('🎉 All Chromium verification checks PASSED!')
    
except Exception as e:
    print(f'❌ Verification failed: {type(e).__name__}: {str(e)}')
    sys.exit(1)
"""

echo "======================================"
echo "🎉 Build completed successfully!"
echo "✅ Dependencies installed"
echo "✅ Chromium installed and verified"
echo "======================================"