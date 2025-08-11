#!/usr/bin/env bash
# Add Chrome to PATH for Selenium to find the binary
export PATH="${PATH}:/opt/render/project/.render/chrome/opt/google/chrome"  #:contentReference[oaicite:14]{index=14}
# Launch the Telegram bot
exec python main.py
