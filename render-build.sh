#!/usr/bin/env bash
# exit on error
set -o errexit

# Directory for cached binaries on Render
STORAGE_DIR=/opt/render/project/.render

# Install Chrome if not cached
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "Downloading and installing Google Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome  # extract without root
  rm google-chrome-stable_current_amd64.deb
  cd $HOME/project/src  # return to project directory
else
  echo "Chrome is cached, using existing binary."
fi

# Install ChromeDriver if not cached
if [[ ! -f $STORAGE_DIR/chromedriver/chromedriver ]]; then
  echo "Downloading Chromedriver..."
  mkdir -p $STORAGE_DIR/chromedriver
  cd $STORAGE_DIR/chromedriver
  # Use a ChromeDriver version matching the Chrome version installed.
  # The URL below should be updated to match the Chrome stable version.
  wget -q https://storage.googleapis.com/chrome-for-testing-public/124.0.6367.78/linux64/chromedriver-linux64.zip
  unzip -q chromedriver-linux64.zip
  mv chromedriver-linux64/chromedriver .
  rm -rf chromedriver-linux64 chromedriver-linux64.zip
  cd $HOME/project/src
else
  echo "Chromedriver is cached, using existing binary."
fi

# (Optional) Check Chrome version for debugging
$STORAGE_DIR/chrome/opt/google/chrome/google-chrome --version || true

# Install Python dependencies
pip install -r requirements.txt

# Note: Chrome's binary path will be added to PATH in the start command (see start.sh).
