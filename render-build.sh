#!/usr/bin/env bash  
# exit on error  
set -o errexit

# Տեղադրել Chrome-ը cache directorի մեջ (եթե արդեն չկա)
STORAGE_DIR=/opt/render/project/.render
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "Downloading Google Chrome stable..."  
  mkdir -p $STORAGE_DIR/chrome  
  cd $STORAGE_DIR/chrome  
  wget -q -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb  
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome  
  rm ./google-chrome-stable_current_amd64.deb  
  cd -  
else  
  echo "Using cached Chrome at $STORAGE_DIR/chrome"  
fi

# Տեղադրել Python requirements փաթեթները
pip install -r requirements.txt
