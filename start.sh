#!/usr/bin/env bash
# exit on error
set -o errexit

# Set environment variables for Chrome binary and Chromedriver
export GOOGLE_CHROME_BIN="/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
export CHROMEDRIVER_PATH="/opt/render/project/.render/chromedriver/chromedriver"

# Optionally, add Chrome to PATH (not strictly required if GOOGLE_CHROME_BIN is set)
export PATH="$PATH:/opt/render/project/.render/chrome/opt/google/chrome"

# Start the Telegram bot
python main.py
