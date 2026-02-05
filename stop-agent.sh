#!/bin/bash

echo "🛑 Stopping Ultimate Local AI Agent..."

# Kill Python agent processes
pkill -f "uvicorn.*app.main:app" 2>/dev/null && echo "✅ Python agent stopped" || echo "⚠️  No Python agent running"
pkill -f "python.*uvicorn" 2>/dev/null

# Kill Node processes (legacy)
pkill -f "node.*server" 2>/dev/null
pkill -f "tsx src/telegram" 2>/dev/null
pkill -f "npm start" 2>/dev/null

# Clear ports
for port in 3000 5173 3001 8000 8001; do
    PID=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null
        echo "✅ Cleared port $port"
    fi
done

# Remove PID file if exists
if [ -f .agent.pid ]; then
    rm .agent.pid
    echo "✅ Removed PID file"
fi

echo "✅ Cleanup complete"
