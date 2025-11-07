#!/bin/bash
set -e

echo "=== Railway Build Script ==="
echo "Current directory: $(pwd)"
echo "Contents: $(ls -la)"
echo "Parent directory contents: $(ls -la .. 2>/dev/null || echo 'Cannot access parent')"

# Copy engine and ai directories
# If running from repo root, copy from current directory into backend/
# If running from backend/, copy from parent directory
if [ -d "engine" ] && [ -d "ai" ]; then
  echo "✓ Engine and AI directories already in current directory"
  # If we're in repo root, copy to backend/
  if [ ! -d "backend/engine" ] && [ -d "backend" ]; then
    echo "✓ Copying engine and ai to backend/..."
    cp -r engine backend/
    cp -r ai backend/
  fi
elif [ -d "../engine" ] && [ -d "../ai" ]; then
  echo "✓ Found ../engine and ../ai, copying to current directory..."
  cp -r ../engine .
  cp -r ../ai .
  echo "✓ Engine and AI copied successfully"
else
  echo "✗ ERROR: Cannot find engine or ai directories"
  echo "Searched in: ./, ../"
  exit 1
fi

# Verify copies
if [ ! -d "engine" ] || [ ! -d "ai" ]; then
  echo "✗ ERROR: Failed to copy engine or ai directories"
  exit 1
fi

echo "✓ Verified: engine and ai directories exist"
echo "Engine contents: $(ls engine/ || echo 'empty')"
echo "AI contents: $(ls ai/ || echo 'empty')"

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "=== Build completed successfully! ==="

