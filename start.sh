#!/usr/bin/env bash
set -o errexit
# Add Chrome and ChromeDriver to PATH
export PATH="$PATH:/opt/render/project/.render/chrome/opt/google/chrome"
export PATH="$PATH:/opt/render/project/.render/chromedriver"
# Start the Python bot script
python main.py
