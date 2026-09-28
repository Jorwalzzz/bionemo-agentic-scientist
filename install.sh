#!/usr/bin/env bash
# Agentic BioNeMo - Unix/macOS/Linux Automated Setup Script
# Run with: curl -sSL https://raw.githubusercontent.com/Jorwalzzz/bionemo-agentic-scientist/main/install.sh | bash

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "\n${GREEN}============================================================"
echo " NVIDIA BioNeMo - Agentic AI Drug Discovery Scientist"
echo " Automated Unix/macOS Setup"
echo -e "============================================================${NC}\n"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] python3 is required but not found.${NC}"
    echo "  macOS: brew install python3"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    exit 1
fi

PY_VERSION=$(python3 --version)
echo -e "${GREEN}[OK] ${PY_VERSION} found.${NC}"

# Clone or update repo
TARGET_DIR="$HOME/bionemo-agentic-scientist"
if [ -d "$TARGET_DIR" ]; then
    echo -e "${GREEN}[OK] Repository exists at $TARGET_DIR — pulling updates...${NC}"
    git -C "$TARGET_DIR" pull origin main
else
    echo -e "${CYAN}[INFO] Cloning repository...${NC}"
    git clone https://github.com/Jorwalzzz/bionemo-agentic-scientist.git "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${CYAN}[INFO] Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate and install
echo -e "${CYAN}[INFO] Installing dependencies (this may take 2-3 minutes)...${NC}"
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}[OK] Dependencies installed.${NC}"

# Create .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        printf "NVIDIA_API_KEY=\nMOCK_MODE=true\n" > .env
    fi
    echo -e "${GREEN}[OK] Config created - free Mock Mode active by default.${NC}"
    echo -e "${YELLOW}OPTIONAL: Edit .env and add your NVIDIA_API_KEY for live GPU inference.${NC}"
fi

echo -e "\n${GREEN}============================================================"
echo " Launching Agentic BioNeMo on http://localhost:8000"
echo -e "============================================================${NC}\n"

# Open browser
(sleep 2 && (xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null)) &

python3 serve_cockpit.py
