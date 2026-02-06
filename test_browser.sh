#!/bin/bash
# Quick test script for browser automation

echo "🧪 Testing Browser Automation"
echo "=============================="
echo ""

cd /home/zeds/Desktop/ultimate-agent/python-agent
source venv/bin/activate

python3 << 'EOF'
import asyncio
from app.integrations.browser_controller import get_browser_controller

async def test_browser():
    print("🔍 Detecting available browsers...")
    browser = get_browser_controller()

    if browser.available_browsers:
        print(f"✅ Found: {', '.join(browser.available_browsers.keys())}")
    else:
        print("⚠️  No browsers detected, will use xdg-open")

    print("\n🌐 Testing browser open (Facebook)...")
    result = await browser.open_url('https://www.facebook.com/')

    if result.success:
        print(f"✅ {result.message}")
        print("\n📝 Notes:")
        print("   - Browser should open to Facebook")
        print("   - Use your saved credentials to login")
        print("   - Browser will stay open for manual posting")
    else:
        print(f"❌ {result.message}")
        if result.error:
            print(f"   Error: {result.error}")

    return result.success

try:
    success = asyncio.run(test_browser())
    print("\n" + "="*50)
    if success:
        print("✅ BROWSER AUTOMATION: WORKING")
    else:
        print("❌ BROWSER AUTOMATION: FAILED")
    print("="*50)
except Exception as e:
    print(f"\n❌ Test failed: {e}")

EOF
