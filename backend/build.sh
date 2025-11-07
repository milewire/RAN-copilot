#!/bin/bash
set -e

# Copy engine and ai directories from parent directory
# This script runs during Railway build when root directory is set to backend/
if [ -d "../engine" ]; then
  echo "Copying engine directory..."
  cp -r ../engine .
fi

if [ -d "../ai" ]; then
  echo "Copying ai directory..."
  cp -r ../ai .
fi

# Install dependencies
pip install -r requirements.txt

echo "Build completed successfully!"

