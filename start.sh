#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load fnm if available
if [ -d "$HOME/.local/share/fnm" ]; then
    export PATH="$HOME/.local/share/fnm:$PATH"
    eval "$(fnm env --use-on-cd)"
fi

# Load nvm if available
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    source "$HOME/.nvm/nvm.sh"
fi

# Parse command line arguments
SKIP_INSTALL=false
if [ "$1" = "--fast" ] || [ "$1" = "-f" ]; then
    SKIP_INSTALL=true
    echo "⚡ Fast mode: Skipping dependency installation"
fi

echo "🚀 Starting Deep RAG..."
echo "================================"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "✅ Created .env file. Please configure it before running."
    exit 1
fi

if [ "$SKIP_INSTALL" = false ]; then
    echo "📦 Checking Backend Dependencies..."
    cd "$PROJECT_DIR"
    if [ ! -d "venv" ]; then
        echo "   Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -q -U pip
        pip install -q -r requirements.txt
        echo "✅ Backend dependencies installed"
    else
        echo "   Skipping (venv exists, use 'pip install -r requirements.txt' to update)"
    fi

    echo "📦 Checking Frontend Dependencies..."
    cd "$PROJECT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        echo "   Installing npm packages..."
        npm install --silent
        echo "✅ Frontend dependencies installed"
    else
        echo "   Skipping (node_modules exists, use 'npm install' to update)"
    fi
fi

echo "🔧 Starting Backend Server..."
cd "$PROJECT_DIR"
source venv/bin/activate
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend server started (PID: $BACKEND_PID, Port: 8000)"

sleep 2

echo "🎨 Starting Frontend Server..."
cd "$PROJECT_DIR/frontend"

# Find the correct Node.js and npm
if [ -d "$HOME/.local/share/fnm" ]; then
    # Use fnm's default Node.js version
    LATEST_NODE=$(ls -1 "$HOME/.local/share/fnm/node-versions" | sort -V | tail -1)
    NODE_PATH="$HOME/.local/share/fnm/node-versions/$LATEST_NODE/installation/bin/node"
    NPM_PATH="$HOME/.local/share/fnm/node-versions/$LATEST_NODE/installation/bin/npm"
elif [ -s "$HOME/.nvm/nvm.sh" ]; then
    source "$HOME/.nvm/nvm.sh"
    NODE_PATH=$(which node)
    NPM_PATH=$(which npm)
else
    NODE_PATH=$(which node)
    NPM_PATH=$(which npm)
fi

echo "Using Node.js: $NODE_PATH ($("$NODE_PATH" --version))"
echo "Using npm: $NPM_PATH ($("$NPM_PATH" --version))"

# Set PATH for the subprocess to include the Node.js binary directory
export PATH="$(dirname "$NODE_PATH"):$PATH"

nohup "$NPM_PATH" run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend server started (PID: $FRONTEND_PID, Port: 5173)"

sleep 3

echo ""
echo "🎉 Deep RAG is running!"
echo "================================"
echo "📊 Backend:  http://localhost:8000"
echo "🌐 Frontend: http://localhost:5173"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "💡 Quick commands:"
echo "   Stop:    ./stop.sh"
echo "   Restart: ./restart.sh         (fast mode by default)"
echo "   Fast:    ./start.sh --fast    (skip dependency check)"
echo "   Full:    ./restart.sh --full  (with dependency check)"
echo ""

if command -v open > /dev/null; then
    sleep 2
    open http://localhost:5173
elif command -v xdg-open > /dev/null; then
    sleep 2
    xdg-open http://localhost:5173
fi