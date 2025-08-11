#!/usr/bin/env bash  
set -o errexit

# Ավելացնել Chrome-ի binary-ի ուղին PATH փոփոխականի մեջ  
export PATH="/opt/render/project/.render/chrome/opt/google/chrome:$PATH"  
echo "Chrome path added. Starting bot..."

# Գործարկել Python բոտը  
python main.py
