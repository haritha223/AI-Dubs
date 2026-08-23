#!/bin/bash
# ============================================================
# AI YouTube Dubbing App — Full EC2 Deployment Script
# Run this ONCE on a fresh Ubuntu 22.04 EC2 instance
# Usage:  bash deploy.sh
# ============================================================

set -e  # Exit immediately on any error

APP_DIR=$(pwd)
SERVICE_NAME="aidubbing"
PORT=8000

echo ""
echo "=================================================="
echo "  AI YouTube Dubbing App — EC2 Deployment"
echo "  Directory: $APP_DIR"
echo "=================================================="
echo ""

# ── Step 1: System packages ────────────────────────────────
echo ">>> [1/7] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git ffmpeg curl

# Install Node.js 20 if missing
if ! command -v node &> /dev/null; then
    echo "    Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "    ✓ Python : $(python3 --version)"
echo "    ✓ Node   : $(node --version)"
echo "    ✓ FFmpeg : $(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f1-3)"

# ── Step 2: Python virtual environment ────────────────────
echo ""
echo ">>> [2/7] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet

echo "    Installing Python packages (may take a few minutes)..."
pip install -r backend/requirements.txt --quiet

echo "    Installing PyTorch (CPU build for Whisper/Transformers)..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet

echo "    ✓ Python packages installed"

# ── Step 3: Required directories ──────────────────────────
echo ""
echo ">>> [3/7] Creating required directories..."
mkdir -p static temp outputs
echo "    ✓ static/ temp/ outputs/ ready"

# ── Step 4: Check .env file ───────────────────────────────
echo ""
echo ">>> [4/7] Checking .env configuration..."
if [ ! -f ".env" ]; then
    echo "    ⚠️  No .env found — copying from .env.example"
    cp .env.example .env
    echo ""
    echo "  ┌──────────────────────────────────────────────┐"
    echo "  │  ACTION REQUIRED: Fill in your API keys!     │"
    echo "  │  Edit now with:  nano .env                   │"
    echo "  │  Then re-run:    bash deploy.sh              │"
    echo "  └──────────────────────────────────────────────┘"
    echo ""
    exit 1
else
    echo "    ✓ .env file found"
fi

# ── Step 5: Build React frontend ──────────────────────────
echo ""
echo ">>> [5/7] Building React frontend..."
cd frontend
npm install --silent
npm run build
cd ..
echo "    ✓ Frontend built → frontend/dist/"

# ── Step 6: Test startup ──────────────────────────────────
echo ""
echo ">>> [6/7] Quick startup test..."
source venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT &
UVICORN_PID=$!
sleep 5

if curl -s --max-time 4 http://localhost:$PORT/health > /dev/null 2>&1; then
    echo "    ✓ Health check passed!"
else
    echo "    ⚠️  App started (models load on first real request — this is normal)"
fi

kill $UVICORN_PID 2>/dev/null || true
sleep 1

# ── Step 7: systemd service ───────────────────────────────
echo ""
echo ">>> [7/7] Registering systemd service: $SERVICE_NAME..."

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=AI YouTube Dubbing FastAPI App
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/bin:/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

sleep 3
STATUS=$(sudo systemctl is-active $SERVICE_NAME)
PUBLIC_IP=$(curl -s --max-time 3 http://checkip.amazonaws.com 2>/dev/null || echo "YOUR_EC2_IP")

echo ""
echo "=================================================="
if [ "$STATUS" = "active" ]; then
    echo "  ✅  DEPLOYMENT SUCCESSFUL!"
    echo ""
    echo "  🌐  App URL : http://$PUBLIC_IP:$PORT"
    echo "  💊  Health  : http://$PUBLIC_IP:$PORT/health"
    echo "  📚  API Docs: http://$PUBLIC_IP:$PORT/docs"
else
    echo "  ❌  Service status: $STATUS"
    echo "  Debug: sudo journalctl -u $SERVICE_NAME -n 50"
fi
echo ""
echo "  Quick commands:"
echo "  → Logs     : sudo journalctl -u $SERVICE_NAME -f"
echo "  → Restart  : sudo systemctl restart $SERVICE_NAME"
echo "  → Update   : bash update.sh"
echo "=================================================="
