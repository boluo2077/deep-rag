#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Default to fast mode, unless --full is specified
FAST_MODE="--fast"
if [ "$1" = "--full" ] || [ "$1" = "-F" ]; then
    FAST_MODE=""
fi

echo "♻️  Restarting Deep RAG..."
echo "================================"

"$PROJECT_DIR/stop.sh"

echo ""
sleep 1

"$PROJECT_DIR/start.sh" $FAST_MODE