#!/usr/bin/env bash
# Add Chrome and Chromedriver to PATH
export PATH="$PATH:/opt/render/project/.render/chrome/opt/google/chrome:/opt/render/project/.render/chromedriver"
# Run the Telegram bot
python main.py
