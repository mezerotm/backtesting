#!/bin/bash
# Rotate Polygon.io API key
# Usage: ./scripts/rotate-polygon-key.sh <NEW_API_KEY>
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <NEW_POLYGON_API_KEY>"
    echo ""
    echo "1. Go to https://polygon.io/dashboard"
    echo "2. Generate a new API key"
    echo "3. Run: $0 <your-new-key>"
    exit 1
fi

NEW_KEY="$1"
ENV_FILE="config/shared/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found. Run from project root."
    exit 1
fi

# Show old key (first 8 chars only)
OLD_LINE=$(grep '^POLYGON_API_KEY=' "$ENV_FILE" 2>/dev/null || echo "not found")
if [ "$OLD_LINE" != "not found" ]; then
    OLD_KEY_PART=$(echo "$OLD_LINE" | sed 's/POLYGON_API_KEY=//' | cut -c1-8)
    echo "Replacing old key starting with: $OLD_KEY_PART..."
else
    echo "No existing POLYGON_API_KEY found. Adding new one."
fi

# Replace the key
if grep -q '^POLYGON_API_KEY=' "$ENV_FILE"; then
    sed -i "s/^POLYGON_API_KEY=.*/POLYGON_API_KEY=$NEW_KEY/" "$ENV_FILE"
else
    echo "POLYGON_API_KEY=$NEW_KEY" >> "$ENV_FILE"
fi

echo "Polygon API key updated successfully in $ENV_FILE"
echo "Restart the backend to pick up the new key."