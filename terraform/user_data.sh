#!/bin/bash
# EC2 instance launch ஆகும்போது automatically run ஆகும்
# Logs: /var/log/user_data.log

set -e
exec > /var/log/user_data.log 2>&1

echo "======================================================"
echo "  AI YouTube Dubbing — EC2 Auto Setup"
echo "  Started: $(date)"
echo "======================================================"

# ── 1. System Packages ─────────────────────────────────────
echo "[1/6] System packages install பண்றோம்..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git ffmpeg curl

# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

echo "  ✓ Python: $(python3 --version)"
echo "  ✓ Node:   $(node --version)"
echo "  ✓ FFmpeg: $(ffmpeg -version 2>&1 | head -n1)"

# ── 2. App Directory & Code ────────────────────────────────
echo ""
echo "[2/6] GitHub-ல இருந்து code clone பண்றோம்..."
APP_DIR="/home/ubuntu/app"
mkdir -p "$APP_DIR"

git clone ${github_repo} "$APP_DIR"
chown -R ubuntu:ubuntu "$APP_DIR"
cd "$APP_DIR"

mkdir -p static temp outputs
echo "  ✓ Code cloned to $APP_DIR"

# ── 3. Python Environment ──────────────────────────────────
echo ""
echo "[3/6] Python virtual environment setup..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet

echo "  Installing Python packages (5-10 mins)..."
pip install -r backend/requirements.txt --quiet

echo "  Installing PyTorch CPU (AI models-க்கு)..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet

echo "  ✓ Python packages ready"

# ── 4. React Frontend Build ────────────────────────────────
echo ""
echo "[4/6] React frontend build பண்றோம்..."
cd frontend
npm install --silent
npm run build
cd ..
echo "  ✓ Frontend built → frontend/dist/"

# ── 5. Environment File ────────────────────────────────────
echo ""
echo "[5/6] .env file create பண்றோம்..."

# Basic .env — API keys-ஐ SSH மூலம் பிறகு add பண்ணுங்க
cat > "$APP_DIR/.env" << 'ENVEOF'
# AI Model Settings
WHISPER_MODEL_NAME=tiny
NLLB_MODEL_NAME=facebook/nllb-200-distilled-600M

# AWS Settings
AWS_DEFAULT_REGION=ap-south-1

# Google TTS (SSH மூலம் EC2-ல login ஆகி fill பண்ணுங்க)
# GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/app/gcp-creds.json
# GOOGLE_CREDENTIALS_JSON=

# AWS S3 (Optional)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_S3_BUCKET=
ENVEOF

chown ubuntu:ubuntu "$APP_DIR/.env"
echo "  ✓ .env created (API keys-ஐ பிறகு SSH மூலம் add பண்ணுங்க)"

# ── 6. Systemd Service ─────────────────────────────────────
echo ""
echo "[6/6] Systemd service register பண்றோம்..."

cat > /etc/systemd/system/aidubbing.service << SERVICEEOF
[Unit]
Description=AI YouTube Dubbing FastAPI App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/bin:/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable aidubbing
systemctl start aidubbing

sleep 5
STATUS=$(systemctl is-active aidubbing)

echo ""
echo "======================================================"
echo "  SETUP COMPLETE! — $(date)"
echo "  Service status: $STATUS"
echo ""
echo "  Commands:"
echo "  → Logs:    sudo journalctl -u aidubbing -f"
echo "  → Restart: sudo systemctl restart aidubbing"
echo "  → Status:  sudo systemctl status aidubbing"
echo "======================================================"
