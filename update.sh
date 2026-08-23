#!/bin/bash
# ============================================================
# AI YouTube Dubbing App — Quick Update Script
# Run this whenever you push new code changes to the server
# Usage:  bash update.sh
# ============================================================

set -e

APP_DIR=$(pwd)
SERVICE_NAME="aidubbing"

echo ""
echo ">>> Pulling latest code..."
git pull

echo ">>> Activating venv & updating Python packages..."
source venv/bin/activate
pip install -r backend/requirements.txt --quiet

echo ">>> Rebuilding frontend..."
cd frontend
npm install --silent
npm run build
cd ..

echo ">>> Restarting service..."
sudo systemctl restart $SERVICE_NAME
sleep 2

STATUS=$(sudo systemctl is-active $SERVICE_NAME)
echo ""
if [ "$STATUS" = "active" ]; then
    echo "  ✅  Update complete! Service is running."
else
    echo "  ❌  Service failed to start. Check: sudo journalctl -u $SERVICE_NAME -n 30"
fi
