#!/usr/bin/env bash
set -o errexit

STORAGE=/opt/render/project/.render

# Install Google Chrome (cached)
if [[ ! -d "$STORAGE/chrome" ]]; then
  echo "Downloading Chrome..."
  mkdir -p "$STORAGE/chrome"
  cd "$STORAGE/chrome"
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb "$STORAGE/chrome"
  rm -f google-chrome-stable_current_amd64.deb
  cd - >/dev/null
else
  echo "Chrome cached."
fi

# Install Chromedriver (cached) — pick a recent version compatible with Chrome
if [[ ! -f "$STORAGE/chromedriver/chromedriver" ]]; then
  echo "Downloading Chromedriver..."
  mkdir -p "$STORAGE/chromedriver"
  cd "$STORAGE/chromedriver"
  # You may update the version below if Chrome updates:
  wget -q https://storage.googleapis.com/chrome-for-testing-public/124.0.6367.78/linux64/chromedriver-linux64.zip
  unzip -q chromedriver-linux64.zip
  mv chromedriver-linux64/chromedriver .
  rm -rf chromedriver-linux64 chromedriver-linux64.zip
  chmod +x chromedriver
  cd - >/dev/null
else
  echo "Chromedriver cached."
fi

# Python deps
pip install -r requirements.txt
