#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "[1/3] Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found. Please install Python 3."
    exit 1
fi

echo "[2/3] Creating virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "[3/3] Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "\nSetup completed successfully!"