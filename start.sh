#!/usr/bin/env bash
set -e

# Install deps (Render also runs render-build.sh, but keep it idempotent)
pip install -r requirements.txt

python main.py
