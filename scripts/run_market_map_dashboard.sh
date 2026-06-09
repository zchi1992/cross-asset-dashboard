#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x ".venv/bin/streamlit" ]; then
  echo "Missing .venv/bin/streamlit. Run: python3 -m venv .venv && .venv/bin/python3 -m pip install -r requirements.txt"
  exit 1
fi

exec .venv/bin/streamlit run dashboard/market_map.py
