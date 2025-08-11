#!/usr/bin/env bash
# exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "Downloading and installing Google Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -q -O chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x chrome.deb $STORAGE_DIR/chrome
  rm chrome.deb
  cd $HOME/project/src || cd $HOME/src || echo "Returned to project directory"
else
  echo "Using cached Google Chrome."
fi

if [[ ! -f $STORAGE_DIR/chromedriver/chromedriver ]]; then
  echo "Downloading ChromeDriver..."
  mkdir -p $STORAGE_DIR/chromedriver
  cd $STORAGE_DIR/chromedriver
  # Determine Chrome version
  CHROME_VER=$($STORAGE_DIR/chrome/opt/google/chrome/google-chrome --product-version || echo "")
  if [[ -n "$CHROME_VER" ]]; then
    DRIVER_URL="https://storage.googleapis.com/chrome-for-testing/$CHROME_VER/linux64/chromedriver-linux64.zip"
    wget -q $DRIVER_URL || wget -q "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VER/linux64/chromedriver-linux64.zip"
    unzip chromedriver-linux64.zip
    mv chromedriver-linux64/chromedriver .
    rm -rf chromedriver-linux64 chromedriver-linux64.zip
  else
    echo "Could not detect Chrome version; installing latest ChromeDriver via pip."
  fi
  cd $HOME/project/src || cd $HOME/src
else
  echo "Using cached ChromeDriver."
fi
