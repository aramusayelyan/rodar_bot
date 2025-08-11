#!/usr/bin/env bash
# exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "Downloading Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  # Download the latest Google Chrome .deb package
  wget -O chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  # Extract Chrome without installing (no root needed):contentReference[oaicite:9]{index=9}
  dpkg -x chrome.deb $STORAGE_DIR/chrome
  rm chrome.deb
  cd $HOME/project/src || cd $HOME/project
else
  echo "Using cached Chrome at $STORAGE_DIR/chrome"
fi

# Install Python dependencies
pip install -r requirements.txt

echo "Build script completed."
