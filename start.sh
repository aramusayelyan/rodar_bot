#!/usr/bin/env bash
set -o errexit

# Put Chrome & Chromedriver on PATH so Selenium finds them
export PATH="$PATH:/opt/render/project/.render/chrome/opt/google/chrome:/opt/render/project/.render/chromedriver"

# Run bot
python main.py
