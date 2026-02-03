#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header() {
    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║  � Ultimate Coding Agent v3.0 - Production Ready           ║${NC}"
    echo -e "${MAGENTA}║  Advanced Memory • Comprehensive Skills • Proactive Automation ║${NC}"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo -e "${CYAN}📍 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

get_port_pid() {
    local port=$1
    lsof -ti:$port 2>/dev/null | awk 'NR==1 {print $2}' || echo ""
}

load_env() {
    if [ -f "$SCRIPT_DIR/.env" ]; then
        export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs -d '\n')
    fi
}

update_env_model() {
    local new_model="$1"
    local env_file="$SCRIPT_DIR/.env"
    
    if [ ! -f "$env_file" ]; then
        return 1
    fi
    
    if grep -q "^OLLAMA_MODEL=" "$env_file"; then
        sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$new_model|" "$env_file"
    else
        echo "OLLAMA_MODEL=$new_model" >> "$env_file"
    fi
}

check_cloud_ollama() {
    echo -e "${CYAN}🌐 Checking Ollama Cloud (free tier)...${NC}" >&2
    
    if [ -n "$OLLAMA_CLOUD_API_KEY" ]; then
        local response
        response=$(curl -s -H "Authorization: Bearer $OLLAMA_CLOUD_API_KEY" \
            "https://api.ollama.com/api/v1/models" 2>/dev/null) || response=""
        
        if echo "$response" | grep -q "qwen"; then
            echo -e "${GREEN}✅ Ollama Cloud available with Qwen models${NC}" >&2
            echo "cloud"
            return 0
        fi
    fi
    
    echo -e "${YELLOW}⚠️  Ollama Cloud not available (no API key or quota)${NC}" >&2
    echo "local"
    return 1
}

detect_best_model() {
    echo -e "${CYAN}🔍 Detecting best available model...${NC}" >&2
    echo "" >&2
    
    local cloud_first=${1:-false}
    
    if [ "$cloud_first" = "true" ]; then
        local cloud_status
        cloud_status=$(check_cloud_ollama 2>/dev/null) || cloud_status="local"
        
        if [ "$cloud_status" = "cloud" ]; then
            echo -e "${GREEN}✅ Using Ollama Cloud (qwen3-coder:30b)${NC}" >&2
            echo "ollama-cloud-qwen3-coder-30b"
            return 0
        fi
    fi
    
    local models_json
    models_json=$(curl -s http://127.0.0.1:11434/api/tags 2>/dev/null) || models_json=""
    
    if [ -z "$models_json" ]; then
        echo -e "${RED}❌ Cannot fetch models from Ollama${NC}" >&2
        echo "💡 Make sure Ollama is running: ollama serve"
        exit 1
    fi
    
    local model_names
    model_names=$(echo "$models_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print('\n'.join(models))
" 2>/dev/null) || model_names=""
    
    if [ -z "$model_names" ]; then
        echo -e "${RED}❌ No models found in Ollama${NC}" >&2
        echo "💡 Pull a model first: ollama pull qwen2.5-coder:7b-instruct-q5_K_M"
        exit 1
    fi
    
    echo "Available models:" >&2
    echo "$model_names" >&2
    echo "" >&2
    
    local priority_patterns="qwen3-coder qwen2.5-coder deepseek-coder codellama llama3.1 llama3"
    
    if [ -n "$OLLAMA_MODEL" ]; then
        if echo "$model_names" | grep -qx "$OLLAMA_MODEL" 2>/dev/null; then
            echo -e "${GREEN}✅ Using user-specified model: $OLLAMA_MODEL${NC}" >&2
            echo "$OLLAMA_MODEL"
            return 0
        fi
        echo -e "${YELLOW}⚠️  User model '$OLLAMA_MODEL' not found, auto-detecting...${NC}" >&2
    fi
    
    for pattern in $priority_patterns; do
        local match
        match=$(echo "$model_names" | grep -i "$pattern" 2>/dev/null | head -1) || match=""
        if [ -n "$match" ]; then
            local clean_model
            clean_model=$(echo "$match" | cut -d':' -f1,2)
            echo -e "${GREEN}✅ Selected: $clean_model${NC}" >&2
            echo "$match"
            return 0
        fi
    done
    
    local first_model
    first_model=$(echo "$model_names" | head -1) || first_model=""
    if [ -n "$first_model" ]; then
        echo -e "${YELLOW}⚠️  No coding model found, using: $first_model${NC}" >&2
        echo "$first_model"
    else
        echo -e "${RED}❌ No models available${NC}" >&2
        exit 1
    fi
}

start_server() {
    print_header
    print_section "🚀 Ultimate Agent - Starting..."
    echo ""
    
    print_section "Step 1: Clearing Ports"
    
    for port in 3000 5173 3001; do
        local PORT_PID
        PORT_PID=$(get_port_pid $port)
        if [ -n "$PORT_PID" ]; then
            echo "🗑️  Killing process on port $port (PID: $PORT_PID)"
            kill -9 $PORT_PID 2>/dev/null || true
            sleep 1
        else
            echo "✅ Port $port is clear"
        fi
    done
    
    echo ""
    print_section "Step 2: Killing Active Instances"
    echo "🔨 Stopping Node.js processes..."
    pkill -f "tsx src/telegram" 2>/dev/null || true
    pkill -f "node src/telegram" 2>/dev/null || true
    pkill -f "node src/server" 2>/dev/null || true
    pkill -f "npx tsx" 2>/dev/null || true
    pkill -f "npm start" 2>/dev/null || true
    sleep 2
    echo "✅ All processes cleaned up"
    echo ""
    
    print_section "Step 3: Starting Ollama..."
    
    if ! command -v ollama >/dev/null 2>&1; then
        print_error "Ollama is not installed!"
        echo "📥 Install from: https://ollama.com"
        echo "Run: curl -fsSL https://ollama.com/install.sh | sh"
        exit 1
    fi
    
    if ! pgrep -f "ollama serve" >/dev/null 2>&1; then
        echo "🚀 Starting Ollama service..."
        ollama serve >/dev/null 2>&1 &
        sleep 5
    fi
    
    if curl -s --connect-timeout 5 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        print_success "Ollama is running"
    else
        print_error "Ollama is not responding"
        echo "💡 Try: ollama serve"
        exit 1
    fi
    
    echo ""
    print_section "Step 4: Detecting Best Model (Cloud First)..."
    
    local cloud_first="true"
    [ "$USE_CLOUD_FIRST" = "false" ] && cloud_first="false"
    
    SELECTED_MODEL=$(detect_best_model $cloud_first)
    update_env_model "$SELECTED_MODEL"
    export OLLAMA_MODEL="$SELECTED_MODEL"
    echo ""
    echo "📦 Model configured: $SELECTED_MODEL"
    echo ""
    
    print_section "Step 5: Verifying Credentials..."
    load_env
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your_telegram_bot_token_here" ]; then
        print_warning "TELEGRAM_BOT_TOKEN not set in .env"
        echo "💡 Get token from: @BotFather"
    else
        echo "✅ Telegram configured"
    fi
    
    if [ -z "$ADMIN_TELEGRAM_ID" ] || [ "$ADMIN_TELEGRAM_ID" = "123456789" ]; then
        print_warning "ADMIN_TELEGRAM_ID not set"
        echo "💡 Get ID from: @userinfobot"
    else
        echo "✅ Admin ID configured"
    fi
    
    echo ""
    print_section "Step 6: Starting Ultimate Agent..."
    cd "$SCRIPT_DIR"
    mkdir -p data workspaces outputs logs memory
    
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🦞 Ultimate Coding Agent v3.0 - Starting...                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 Dashboard: http://localhost:3000"
    echo "🦙 Ollama:    http://localhost:11434"
    echo "📦 Model:     $SELECTED_MODEL"
    echo ""
    echo "🎯 Commands (type in Telegram):"
    echo "   /build • /code • /fix • /status • /heartbeat • /skills"
    echo "   /memory • /post • /deploy • /analytics • /security • /learn"
    echo ""
    echo "📊 Dashboard buttons:"
    echo "   Build • Code • Social • DevOps • Analytics • Settings"
    echo ""
    
    npm start
}

start_dashboard() {
    print_header
    print_section "🌐 Starting Dashboard Only..."
    
    cd "$SCRIPT_DIR"
    mkdir -p data workspaces outputs logs
    
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  📊 Dashboard Mode - No Telegram Bot                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 Dashboard: http://localhost:3000"
    echo "🦙 Ollama:    http://localhost:11434"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    
    npx tsx src/server.ts
}

start_telegram() {
    print_header
    print_section "📱 Starting Telegram Bot Only..."
    
    cd "$SCRIPT_DIR"
    mkdir -p data workspaces outputs logs
    
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  📱 Telegram Mode - No Dashboard                            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🦙 Ollama:    http://localhost:11434"
    echo "📦 Model:     $(detect_best_model)"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    
    npx tsx src/telegram.ts
}

stop_server() {
    print_header
    echo "🛑 Stopping Ultimate Agent..."
    echo ""
    
    pkill -f "node.*server" 2>/dev/null || true
    pkill -f "tsx src/telegram" 2>/dev/null || true
    pkill -f "npm start" 2>/dev/null || true
    sleep 2
    
    for port in 3000 5173 3001; do
        local PORT_PID
        PORT_PID=$(get_port_pid $port)
        if [ -n "$PORT_PID" ]; then
            kill -9 $PORT_PID 2>/dev/null || true
        fi
    done
    
    print_success "Server stopped"
}

restart_server() {
    print_header
    echo "🔄 Restarting Ultimate Agent..."
    echo ""
    stop_server
    sleep 2
    start_server
}

show_status() {
    print_header
    echo "📊 System Status"
    echo ""
    
    if pgrep -f "node.*server" >/dev/null 2>&1; then
        echo -e "${GREEN}🟢 Dashboard: RUNNING${NC}"
        local SERVER_PID
        SERVER_PID=$(pgrep -f "node.*server" | head -1)
        echo "   PID: $SERVER_PID"
    else
        echo -e "${RED}🔴 Dashboard: STOPPED${NC}"
    fi
    
    if pgrep -f "tsx src/telegram" >/dev/null 2>&1; then
        echo -e "${GREEN}🟢 Telegram: RUNNING${NC}"
    else
        echo -e "${RED}🔴 Telegram: STOPPED${NC}"
    fi
    
    echo ""
    
    
    if pgrep -f "ollama serve" >/dev/null 2>&1; then
        echo -e "${GREEN}🟢 Ollama: RUNNING${NC}"
    else
        echo -e "${RED}🔴 Ollama: STOPPED${NC}"
    fi
    
    echo ""
    
    load_env
    echo "📦 Model: ${OLLAMA_MODEL:-Auto-detect on start}"
    echo "🌐 Web:   http://localhost:3000"
    echo "🦙 API:   http://localhost:11434"
    echo ""
    echo "🧪 Menu System: ✅ Active (5 categories, breadcrumbs, smart responses)"
}

show_logs() {
    echo "📝 Recent Logs (last 30 lines)"
    echo ""
    
    if [ -f "$SCRIPT_DIR/agent-startup.log" ]; then
        tail -30 "$SCRIPT_DIR/agent-startup.log"
    else
        echo "No logs found. Check terminal output or run server first."
    fi
}

test_system() {
    print_header
    echo "🧪 Running System Tests..."
    echo ""
    
    echo "1. Testing HTTP server..."
    if curl -sf --connect-timeout 5 http://localhost:3000/health >/dev/null 2>&1; then
        print_success "Dashboard is running"
    else
        print_error "Dashboard is not responding"
        echo "   Start with: $0 start or $0 dashboard"
    fi
    
    echo ""
    echo "2. Testing Ollama connection..."
    if curl -sf --connect-timeout 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_success "Ollama is responding"
        echo "   Models available:"
        curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', [])[:5]:
    print(f'   • {m[\"name\"]}')
" 2>/dev/null || true
    else
        print_error "Ollama is not responding"
    fi
    
    echo ""
    echo "3. Testing Telegram bot..."
    if pgrep -f "tsx src/telegram" >/dev/null 2>&1; then
        print_success "Telegram bot is running"
    else
        print_warning "Telegram bot is not running"
    fi
    
    echo ""
    echo "4. Testing Memory System..."
    if [ -d "$SCRIPT_DIR/memory" ]; then
        print_success "Memory directory exists"
    else
        print_error "Memory directory missing"
    fi
    
    echo ""
    echo "5. Testing Database..."
    if [ -f "$SCRIPT_DIR/data/db/interactions.db" ]; then
        print_success "Database exists"
    else
        print_warning "Database not initialized (will be created)"
    fi
    
    echo ""
    print_success "System tests completed"
}

run_tests() {
    print_header
    echo "🧪 Running Menu System Tests..."
    echo ""
    
    cd "$SCRIPT_DIR"
    
    # Test MenuManager
    echo "Testing MenuManager..."
    if npx tsx tests/test_menu_manager.ts 2>&1; then
        print_success "MenuManager tests passed"
    else
        print_error "MenuManager tests failed"
    fi
    
    echo ""
    
    # Test SmartResponse
    echo "Testing SmartResponse..."
    if npx tsx tests/test_smart_response.ts 2>&1; then
        print_success "SmartResponse tests passed"
    else
        print_error "SmartResponse tests failed"
    fi
    
    echo ""
    print_success "All tests completed!"
}

install_deps() {
    print_header
    echo "📦 Installing Dependencies..."
    echo ""
    
    cd "$SCRIPT_DIR"
    
    if [ ! -f "package.json" ]; then
        print_error "package.json not found"
        exit 1
    fi
    
    npm install
    print_success "Dependencies installed"
}

setup_env() {
    print_header
    echo "⚙️  Environment Setup"
    echo ""
    
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            print_success "Created .env from template"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_success ".env already exists"
    fi
    
    echo ""
    echo "📝 Required variables in .env:"
    echo "  • TELEGRAM_BOT_TOKEN - from @BotFather"
    echo "  • ADMIN_TELEGRAM_ID - from @userinfobot"
    echo "  • OLLAMA_MODEL - auto-detected on start"
    echo "  • OLLAMA_CLOUD_API_KEY - optional, for cloud models"
    echo ""
    echo "Edit: nano $SCRIPT_DIR/.env"
}

pull_model() {
    local model="${1:-qwen2.5-coder:7b-instruct-q5_K_M}"
    
    print_header
    echo "📦 Pulling model: $model"
    echo ""
    
    if ! command -v ollama >/dev/null 2>&1; then
        print_error "Ollama is not installed"
        exit 1
    fi
    
    if ! pgrep -f "ollama serve" >/dev/null 2>&1; then
        echo "🚀 Starting Ollama..."
        ollama serve >/dev/null 2>&1 &
        sleep 5
    fi
    
    ollama pull "$model"
    print_success "Model pulled: $model"
}

show_models() {
    print_header
    echo "🧠 Available Ollama Models"
    echo ""
    
    if ! curl -sf --connect-timeout 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_error "Ollama is not responding"
        echo "Start Ollama first: ollama serve"
        exit 1
    fi
    
    curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])

print('Models (' + str(len(models)) + '):')
print('')
for m in models:
    size_mb = m.get('size', 0) / (1024*1024)
    print(f'  • {m[\"name\"]} ({size_mb:.1f} MB)')
"
}

show_help() {
    print_header
    echo -e "${CYAN}Usage: $0 [command]${NC}"
    echo ""
    echo -e "${CYAN}Commands:${NC}"
    echo "  start       Start dashboard + Telegram bot (default)"
    echo "  dashboard   Start dashboard only (no Telegram)"
    echo "  telegram    Start Telegram bot only (no dashboard)"
    echo "  stop        Stop all running servers"
    echo "  restart     Restart all servers"
    echo "  status      Show system status"
    echo "  logs        Show recent logs"
    echo "  test        Run system tests"
    echo "  tests       Run menu system tests (NEW!)"
    echo "  models      List available Ollama models"
    echo "  pull <model> Pull a new Ollama model"
    echo "  install     Install npm dependencies"
    echo "  setup       Create .env file"
    echo "  help        Show this help message"
    echo ""
    echo -e "${CYAN}Environment Variables:${NC}"
    echo "  USE_CLOUD_FIRST=false  Disable cloud model priority"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  $0 start              # Start everything"
    echo "  $0 dashboard          # Dashboard only"
    echo "  $0 telegram           # Telegram only"
    echo "  $0 tests              # Run menu system tests"
    echo "  $0 pull llama3.2      # Pull Llama model"
    echo "  $0 test               # Run diagnostics"
    echo ""
    echo -e "${CYAN}Key Features (v3.0 Enhanced):${NC}"
    echo "  � Enhanced Menu System (5 categories, breadcrumbs, smart responses)"
    echo "  🧠 Knowledge Base (120+ modern development resources)"
    echo "  📱 15-Button Telegram Interface with Smart Navigation"
    echo "  🤖 Advanced Memory System (5 markdown files)"
    echo "  🛠️  Comprehensive Skills Library"
    echo "  💓 Proactive Heartbeat (30-min checks)"
    echo "  🧠 Smart Model Routing (Cloud first, then local)"
    echo "  📊 Live Dashboard (no mock data)"
    echo "  🔒 Security Guardian"
    echo "  📈 Analytics & Self-Improvement"
}

COMMAND=${1:-start}

case "$COMMAND" in
    start)
        start_server
        ;;
    dashboard)
        start_dashboard
        ;;
    telegram)
        start_telegram
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        test_system
        ;;
    tests)
        run_tests
        ;;
    models)
        show_models
        ;;
    pull)
        pull_model "${2:-qwen2.5-coder:7b-instruct-q5_K_M}"
        ;;
    install)
        install_deps
        ;;
    setup)
        setup_env
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
