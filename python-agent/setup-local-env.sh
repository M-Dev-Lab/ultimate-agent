#!/bin/bash
# Local Environment Setup Script for Ultimate Coding Agent
# Prepares your local machine to run the Python agent with Ollama Cloud

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Ultimate Coding Agent - Local Environment Setup              ║"
echo "║   Version 3.0.0 with Ollama Cloud Integration                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check system requirements
echo -e "${BLUE}[1/8]${NC} Checking system requirements..."

command -v python3 &> /dev/null || { echo -e "${RED}✗ Python 3 not found${NC}"; exit 1; }
python_version=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python ${python_version}${NC}"

command -v redis-cli &> /dev/null || { echo -e "${YELLOW}⚠ Redis CLI not found (needed for Celery)${NC}"; }
command -v git &> /dev/null || { echo -e "${RED}✗ Git not found${NC}"; exit 1; }
echo -e "${GREEN}✓ Git installed${NC}"

# Step 2: Check SSH key for Z-Desktop
echo ""
echo -e "${BLUE}[2/8]${NC} Checking SSH configuration..."

SSH_KEY_PATH="/home/zeds/.ssh/id_ed25519"
if [ -f "$SSH_KEY_PATH" ]; then
    echo -e "${GREEN}✓ SSH key found: $SSH_KEY_PATH${NC}"
    chmod 600 "$SSH_KEY_PATH"
    echo -e "${GREEN}✓ SSH key permissions fixed${NC}"
else
    echo -e "${YELLOW}⚠ SSH key not found at $SSH_KEY_PATH${NC}"
    echo "  To use Ollama Cloud, ensure your SSH key is configured."
fi

# Step 3: Create directory structure
echo ""
echo -e "${BLUE}[3/8]${NC} Creating directory structure..."

mkdir -p data/{chroma,workspaces,memory}
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"

# Step 4: Setup Python virtual environment
echo ""
echo -e "${BLUE}[4/8]${NC} Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Step 5: Install dependencies
echo ""
echo -e "${BLUE}[5/8]${NC} Installing Python dependencies..."

pip install --upgrade pip setuptools wheel > /dev/null
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 6: Setup environment configuration
echo ""
echo -e "${BLUE}[6/8]${NC} Setting up environment configuration..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Created .env file from template${NC}"
    echo "  Please update the following in .env:"
    echo "    - JWT_SECRET (generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\")"
    echo "    - OLLAMA_API_KEY (your Ollama Cloud API key)"
    echo "    - Database credentials (if using PostgreSQL)"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Step 7: Verify Ollama Cloud connectivity
echo ""
echo -e "${BLUE}[7/8]${NC} Testing Ollama Cloud connectivity..."

# Read Ollama host from .env
OLLAMA_HOST=$(grep "^OLLAMA_HOST=" .env | cut -d'=' -f2 | tr -d '"')
OLLAMA_API_KEY=$(grep "^OLLAMA_API_KEY=" .env | cut -d'=' -f2 | tr -d '"')

if [ -z "$OLLAMA_API_KEY" ] || [ "$OLLAMA_API_KEY" = "your_ollama_cloud_api_key_here" ]; then
    echo -e "${YELLOW}⚠ Ollama Cloud API key not configured${NC}"
    echo "  Update OLLAMA_API_KEY in .env to connect to Ollama Cloud"
else
    echo -e "${GREEN}✓ Ollama Cloud API key configured${NC}"
    
    # Try to test connectivity (if curl available)
    if command -v curl &> /dev/null; then
        if curl -s -H "Authorization: Bearer $OLLAMA_API_KEY" \
                "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Ollama Cloud connection successful${NC}"
        else
            echo -e "${YELLOW}⚠ Could not verify Ollama Cloud connection${NC}"
            echo "  SSH tunnel may be needed. Check: ssh -L 11434:localhost:11434 z-desktop"
        fi
    fi
fi

# Step 8: Database initialization
echo ""
echo -e "${BLUE}[8/8]${NC} Initializing database..."

python3 << 'PYTHON_SCRIPT'
import os
os.environ.setdefault('ENVIRONMENT', 'development')

try:
    from app.db.session import init_db
    import asyncio
    asyncio.run(init_db())
    print('\033[0;32m✓ Database initialized\033[0m')
except Exception as e:
    print(f'\033[1;33m⚠ Database initialization deferred\033[0m: {e}')
    print('  Run: python -c "from app.db.session import init_db; import asyncio; asyncio.run(init_db())"')
PYTHON_SCRIPT

# Final instructions
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Local Environment Setup Complete! 🎉                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Ensure required services are running:"
echo "   ${YELLOW}Terminal 1:${NC} redis-server"
echo "   ${YELLOW}Terminal 2:${NC} SSH tunnel to Z-Desktop"
echo "             ssh -L 11434:localhost:11434 z-desktop"
echo ""
echo "2. Start the application:"
echo "   ${YELLOW}Terminal 3:${NC} source venv/bin/activate"
echo "             uvicorn app.main:app --reload --port 8000"
echo ""
echo "3. Start Celery worker (optional):"
echo "   ${YELLOW}Terminal 4:${NC} celery -A app.tasks worker --loglevel=info"
echo ""
echo "4. Access the API:"
echo "   ${YELLOW}API Docs:${NC} http://localhost:8000/docs"
echo "   ${YELLOW}Health Check:${NC} http://localhost:8000/api/health/"
echo ""
echo "5. Configuration files:"
echo "   ${YELLOW}.env${NC}                 - Environment variables (UPDATE THESE!)"
echo "   ${YELLOW}app/core/config.py${NC}    - Application settings"
echo ""
echo -e "${YELLOW}Important:${NC} Update the following in .env before running:"
echo "  - JWT_SECRET: Generate a secure key"
echo "  - OLLAMA_API_KEY: Your Ollama Cloud API key"
echo ""
echo "For Ollama Cloud over SSH:"
echo "  ssh -L 11434:localhost:11434 -i ~/.ssh/id_ed25519 zeds@z-desktop"
echo ""
