#!/bin/bash
set -e

echo "Installing AI Service requirements..."

# Upgrade pip first
python -m pip install --upgrade pip

# Install requirements with verbose output
echo "Installing Python packages..."
pip install -r requirements.txt --verbose

# Install Playwright and browsers
echo "Installing Playwright..."
playwright install --with-deps chromium

echo "Verifying installations..."
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import playwright; print(f'Playwright: {playwright.__version__}')"
python -c "import pydantic; print(f'Pydantic: {pydantic.__version__}')"

echo "Installation complete!"