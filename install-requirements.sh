#!/bin/bash
set -e

echo "Installing AI Service requirements..."

# Note: For Render deployment, use build.sh at repo root instead
# This script is for local development/testing

# Upgrade pip first
python -m pip install --upgrade pip

# Install requirements with verbose output
echo "Installing Python packages..."
pip install -r requirements.txt --verbose

# Install Playwright and browsers
echo "Installing Playwright..."
playwright install --with-deps chromium

echo "Verifying installations..."
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')" 2>/dev/null || echo "FastAPI check failed"
python -c "import playwright; print(f'Playwright: {playwright.__version__}')" 2>/dev/null || echo "Playwright check failed"
python -c "import pydantic; print(f'Pydantic: {pydantic.__version__}')" 2>/dev/null || echo "Pydantic check failed"

echo "Local installation complete!"
echo "For production deployment, use build.sh at repo root."