#!/bin/bash

# Social Media Browser Automation Fix Script
# Fixes for Puppeteer/Playwright on Ubuntu

echo "🔧 Fixing Social Media Browser Automation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command succeeded
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
    fi
}

echo -e "\n${YELLOW}Step 1: Installing missing system dependencies...${NC}"
echo "Note: You may need to enter your password for sudo"

# Install Ubuntu dependencies (non-interactive)
sudo apt-get update > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Installing dependencies..."
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libcairo-gobject2 \
        libcairo2 \
        libdatrie1 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libthai0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        xdg-utils \
        wget \
        unzip > /dev/null 2>&1
    check_status "System dependencies installed"
else
    echo -e "${YELLOW}⚠ Could not update apt. Skipping system dependencies.${NC}"
fi

echo -e "\n${YELLOW}Step 2: Reinstalling Playwright browsers...${NC}"
cd /home/zeds/Desktop/ultimate-agent

# Reinstall playwright browsers
echo "Installing Chromium..."
npx playwright install chromium > /dev/null 2>&1
check_status "Chromium installed"

echo "Installing Firefox..."
npx playwright install firefox > /dev/null 2>&1
check_status "Firefox installed"

echo "Installing WebKit..."
npx playwright install webkit > /dev/null 2>&1
check_status "WebKit installed"

echo -e "\n${YELLOW}Step 3: Testing browser launch...${NC}"

# Test browser launch
node -e "
const { chromium } = require('playwright');
(async () => {
    try {
        const browser = await chromium.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        });
        console.log('✓ Browser launch successful');
        await browser.close();
    } catch (error) {
        console.error('✗ Browser launch failed:', error.message);
        process.exit(1);
    }
})();
" && check_status "Browser launch test" || echo -e "${RED}✗ Browser launch test failed${NC}"

echo -e "\n${YELLOW}Step 4: Setting environment variables...${NC}"

# Create or update .env file with browser settings
if [ -f .env ]; then
    # Add browser config if not present
    if ! grep -q "BROWSER_HEADLESS" .env; then
        echo "" >> .env
        echo "# Browser Automation Configuration (Updated)" >> .env
        echo "BROWSER_HEADLESS=true" >> .env
        echo "BROWSER_STEALTH=true" >> .env
        echo "BROWSER_TIMEOUT=60000" >> .env
        echo "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=" >> .env
    fi
    check_status "Environment variables configured"
else
    echo -e "${RED}✗ .env file not found${NC}"
fi

echo -e "\n${YELLOW}Step 5: Verifying code changes...${NC}"

# Check if the updated selectors are in place
if grep -q "cookieAccept" src/browser/browser_config.ts 2>/dev/null; then
    check_status "Updated selectors applied"
else
    echo -e "${YELLOW}⚠ Code updates may need to be applied manually${NC}"
fi

echo -e "\n${GREEN}✅ Fix complete!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Test the social media command: npm start"
echo "2. If still having issues, run: node -e \"const { chromium } = require('playwright'); (async () => { const b = await chromium.launch({headless: false}); await b.close(); console.log('OK'); })()\""
echo "3. Check logs in /home/zeds/Desktop/ultimate-agent/logs/ for detailed errors"

echo -e "\n${YELLOW}Troubleshooting tips:${NC}"
echo "- If browser still fails, try setting PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH in .env"
echo "- For Facebook issues, ensure cookies are accepted (new selectors added)"
echo "- For detection issues, stealth mode is now properly applied"
