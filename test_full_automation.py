#!/usr/bin/env python3
"""
Test Full Social Media Automation
"""

import asyncio
import sys
sys.path.insert(0, './python-agent')

async def test_automation():
    print("\n" + "="*70)
    print("🤖 TESTING FULL SOCIAL MEDIA AUTOMATION")
    print("="*70)

    from app.integrations.social_automation_bot import get_social_bot

    bot = get_social_bot()

    # Test Facebook automation
    print("\n1️⃣ Testing Facebook Full Automation")
    print("-"*70)

    test_content = "🤖 Test post from Ultimate Agent - Full automation test!"

    result = await bot.post_to_facebook(test_content)

    print(f"\n✅ Success: {result.get('success')}")
    print(f"📄 Message: {result.get('message')}")
    print(f"🔐 Requires Login: {result.get('requires_login', False)}")

    print("\n" + "="*70)
    if result.get('success'):
        print("✅ ✅ ✅  FULL AUTOMATION WORKING  ✅ ✅ ✅")
        print("\n📊 What happened:")
        print("   1. ✅ Undetected Chrome launched")
        print("   2. ✅ Navigated to Facebook")
        print("   3. ✅ Found post creation box")
        print("   4. ✅ Typed content with human-like delays")
        print("   5. ✅ Clicked Post button")
        print("   6. ✅ Post submitted!")
    elif result.get('requires_login'):
        print("⚠️  LOGIN REQUIRED")
        print("\n📊 Next Steps:")
        print("   1. Browser is open to Facebook")
        print("   2. Please login in the opened browser")
        print("   3. Once logged in, try the automation again")
    else:
        print("❌ AUTOMATION FAILED")
        print(f"\nError: {result.get('message')}")

    print("="*70 + "\n")

    # Keep browser open
    print("Browser will remain open for 30 seconds...")
    await asyncio.sleep(30)

    bot.close()

if __name__ == "__main__":
    asyncio.run(test_automation())
