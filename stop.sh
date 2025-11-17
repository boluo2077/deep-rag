#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🛑 Stopping Deep RAG..."
echo "================================"

# Stop backend (port 8000)
BACKEND_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null
    echo "✅ Backend server stopped (PID: $BACKEND_PID)"
else
    echo "⚠️  Backend server not running"
fi

# Stop frontend (port 5173)
FRONTEND_PID=$(lsof -ti:5173 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Frontend server stopped (PID: $FRONTEND_PID)"
else
    echo "⚠️  Frontend server not running"
fi

# Clean up PID files if they exist
rm -f "$PROJECT_DIR/.backend.pid" "$PROJECT_DIR/.frontend.pid" 2>/dev/null

echo ""
echo "✅ Deep RAG stopped!"
echo "================================"