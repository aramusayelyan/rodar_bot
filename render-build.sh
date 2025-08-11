#!/usr/bin/env bash
# exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

# Install Google Chrome to cached directory if not present
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "Downloading Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -q -O chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x chrome.deb $STORAGE_DIR/chrome
  rm chrome.deb
  cd - > /dev/null
else
  echo "Chrome is cached."
fi

# Install ChromeDriver to cached directory if not present
if [[ ! -d $STORAGE_DIR/chromedriver ]]; then
  echo "Downloading ChromeDriver..."
  mkdir -p $STORAGE_DIR/chromedriver
  # Get latest stable ChromeDriver version
  LATEST_CHROMEDRIVER=$(wget -q -O - https://chromedriver.storage.googleapis.com/LATEST_RELEASE)
  wget -q -O $STORAGE_DIR/chromedriver/chromedriver_linux64.zip "https://chromedriver.storage.googleapis.com/${LATEST_CHROMEDRIVER}/chromedriver_linux64.zip"
  # Install unzip if not already available
  apt-get update && apt-get install -y unzip >/dev/null
  unzip $STORAGE_DIR/chromedriver/chromedriver_linux64.zip -d $STORAGE_DIR/chromedriver
  rm $STORAGE_DIR/chromedriver/chromedriver_linux64.zip
  # Ensure chromedriver binary is executable
  chmod +x $STORAGE_DIR/chromedriver/chromedriver
else
  echo "ChromeDriver is cached."
fi

# Install Python dependencies
pip install -r requirements.txt
