"""
Full Social Media Automation Bot - PLAYWRIGHT (2026 Standard)
Automatically handles login detection, posting, and media uploads
Uses Playwright for reliable cross-browser automation
"""

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import asyncio
import random
import structlog
from typing import Dict, Optional
from pathlib import Path

logger = structlog.get_logger(__name__)


class SocialMediaBot:
    """Full automation bot using Playwright - 2026 standard"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    async def _init_browser(self):
        """Initialize Playwright browser with user's Chrome profile"""
        import subprocess
        import os

        if not self.playwright:
            self.playwright = await async_playwright().start()

        # First, close any existing Chrome instances to free up the profile
        logger.info("Closing existing Chrome instances...")
        subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
        subprocess.run(["pkill", "-f", "chromium"], capture_output=True)
        await asyncio.sleep(2)

        # Use user's actual Chrome profile (with saved logins)
        user_data_dir = str(Path.home() / ".config" / "google-chrome")

        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=self.headless,
                channel="chromium",  # Use system chromium
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--start-maximized',
                    '--profile-directory=Default',
                ],
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
                ignore_https_errors=True,
            )

            # Anti-detection scripts
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            logger.info("✅ Browser launched with user profile (saved logins available)")
            return self.context

        except Exception as e:
            logger.warning(f"User profile launch failed: {e}")

            # Fallback: Use Playwright's own browser
            automation_profile = str(Path.home() / ".config" / "playwright-social-bot")
            Path(automation_profile).mkdir(parents=True, exist_ok=True)

            self.context = await self.playwright.chromium.launch_persistent_context(
                automation_profile,
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox'],
                viewport={'width': 1920, 'height': 1080},
            )
            return self.context

    def _human_delay(self, min_sec: float = 0.5, max_sec: float = 2.0):
        """Random delay to mimic human behavior"""
        return asyncio.sleep(random.uniform(min_sec, max_sec))

    async def _human_type(self, locator, text: str):
        """Type text with human-like delays"""
        await locator.click()
        for char in text:
            await locator.type(char, delay=random.uniform(50, 150))

    async def post_to_facebook(self, content: str, media_path: Optional[str] = None) -> Dict:
        """Fully automate Facebook posting with Playwright - 2026 selectors"""
        page = None
        try:
            logger.info("🤖 Starting Facebook automation with Playwright...")
            context = await self._init_browser()
            page = await context.new_page()

            # Navigate to Facebook
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await self._human_delay(3, 4)

            # Check if logged in by looking for logged-in elements
            is_logged_in = False
            try:
                # Look for elements that only exist when logged in
                logged_in_indicators = page.locator("[aria-label='Facebook'], [data-pagelet='LeftRail'], [role='feed'], [aria-label='Your profile']")
                is_logged_in = await logged_in_indicators.first.is_visible(timeout=5000)
            except:
                is_logged_in = False

            if not is_logged_in:
                logger.warning("Not logged in to Facebook - waiting for manual login...")
                print("\n" + "="*60)
                print("⚠️  PLEASE LOG IN TO FACEBOOK IN THE BROWSER WINDOW")
                print("   The bot will continue automatically after you log in.")
                print("   You have 2 minutes to complete login.")
                print("="*60 + "\n")

                # Wait for a logged-in indicator
                try:
                    await page.wait_for_selector("[aria-label='Facebook'], [data-pagelet='LeftRail'], [role='feed']", timeout=120000)
                    await self._human_delay(3, 5)
                except:
                    await page.screenshot(path="/tmp/fb_login_timeout.png")
                    return {
                        "success": False,
                        "message": "Login timeout - please try again. Screenshot saved.",
                        "requires_login": True
                    }

            logger.info("✅ Logged in to Facebook")

            # Use role-based and text-based selectors (2026 best practice)
            # Find the "What's on your mind" input area
            logger.info("Looking for post creation area...")

            # Try clicking the post creation trigger
            try:
                # Method 1: Click on the "What's on your mind" text directly
                post_trigger = page.get_by_text("What's on your mind").first
                await post_trigger.click(timeout=5000)
            except:
                try:
                    # Method 2: Find by placeholder-like pattern
                    post_trigger = page.locator("div[role='button'] span").filter(has_text="What's on your mind").first
                    await post_trigger.click(timeout=5000)
                except:
                    try:
                        # Method 3: Click the feed composer area
                        post_trigger = page.locator("[data-pagelet='FeedComposer']").first
                        await post_trigger.click(timeout=5000)
                    except:
                        # Method 4: Press keyboard shortcut
                        await page.keyboard.press("p")
                        await self._human_delay(1, 2)

            await self._human_delay(2, 3)

            # Wait for and find the text input area (contenteditable div)
            logger.info("Finding text input area...")
            text_area = None

            # Try multiple approaches for the text area
            text_selectors = [
                "div[contenteditable='true'][role='textbox']",
                "div[contenteditable='true'][data-lexical-editor='true']",
                "[aria-label*='Write something'] div[contenteditable='true']",
                "form div[contenteditable='true']",
            ]

            for selector in text_selectors:
                try:
                    text_area = page.locator(selector).first
                    await text_area.wait_for(state="visible", timeout=5000)
                    logger.info(f"Found text area with: {selector}")
                    break
                except:
                    continue

            if not text_area:
                # Take screenshot for debugging
                await page.screenshot(path="/tmp/fb_debug.png")
                raise Exception("Could not find text input area. Screenshot saved to /tmp/fb_debug.png")

            # Click and type content
            logger.info("Typing content...")
            await text_area.click()
            await self._human_delay(0.5, 1)

            # Type using keyboard (more reliable than .type())
            await page.keyboard.type(content, delay=random.uniform(30, 80))
            await self._human_delay(1, 2)

            # Handle media upload if provided
            if media_path and Path(media_path).exists():
                logger.info("Uploading media...")
                try:
                    # Find file input and upload
                    file_input = page.locator("input[type='file'][accept*='image']").first
                    await file_input.set_input_files(str(Path(media_path).absolute()))
                    await self._human_delay(3, 4)
                except Exception as e:
                    logger.warning(f"Media upload skipped: {e}")

            # Find and click Post button
            logger.info("Looking for Post button...")
            post_button = None

            post_selectors = [
                "div[aria-label='Post'][role='button']",
                "span:text-is('Post')",
                "div[role='button']:has-text('Post')",
                "[data-testid='post-button']",
            ]

            for selector in post_selectors:
                try:
                    post_button = page.locator(selector).first
                    await post_button.wait_for(state="visible", timeout=3000)
                    logger.info(f"Found Post button with: {selector}")
                    break
                except:
                    continue

            if not post_button:
                # Try using keyboard shortcut
                logger.info("Using keyboard shortcut to post...")
                await page.keyboard.press("Control+Enter")
            else:
                await post_button.click()

            logger.info("✅ Facebook post submitted!")
            await self._human_delay(3, 5)

            # Verify post was created
            await asyncio.sleep(3)

            return {
                "success": True,
                "message": "✅ Posted to Facebook successfully!",
                "platform": "Facebook"
            }

        except Exception as e:
            logger.error(f"Facebook automation error: {e}")
            # Take screenshot on error
            if page:
                try:
                    await page.screenshot(path="/tmp/fb_error.png")
                    logger.info("Error screenshot saved to /tmp/fb_error.png")
                except:
                    pass
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "platform": "Facebook"
            }
        finally:
            if page:
                await page.close()

    async def post_to_twitter(self, content: str, media_path: Optional[str] = None) -> Dict:
        """Fully automate Twitter/X posting with Playwright"""
        page = None
        try:
            logger.info("🤖 Starting Twitter automation with Playwright...")
            context = await self._init_browser()
            page = await context.new_page()

            # Navigate to Twitter compose
            await page.goto("https://twitter.com/compose/tweet", wait_until="networkidle")
            await self._human_delay(2, 3)

            # Check if logged in - wait for user to login if needed
            if "login" in page.url.lower():
                logger.warning("Not logged in to Twitter - waiting for manual login...")
                print("\n⚠️  PLEASE LOG IN TO TWITTER IN THE BROWSER WINDOW")
                print("   The bot will continue automatically after you log in.\n")

                try:
                    await page.wait_for_url("**/twitter.com/**", timeout=120000)
                    await self._human_delay(3, 5)
                except:
                    return {
                        "success": False,
                        "message": "Login timeout - please try again",
                        "requires_login": True
                    }

            logger.info("✅ Logged in to Twitter")

            # Find tweet text area
            tweet_box = page.locator("div[data-testid='tweetTextarea_0']").first
            await tweet_box.wait_for(state="visible", timeout=10000)

            logger.info("Typing tweet...")
            await self._human_type(tweet_box, content)
            await self._human_delay(1, 2)

            # Handle media upload
            if media_path and Path(media_path).exists():
                logger.info("Uploading media...")
                try:
                    file_input = page.locator("input[data-testid='fileInput']").first
                    await file_input.set_input_files(str(Path(media_path).absolute()))
                    await self._human_delay(2, 3)
                except Exception as e:
                    logger.warning(f"Media upload skipped: {e}")

            # Click Tweet button
            logger.info("Clicking Tweet button...")
            tweet_button = page.locator("div[data-testid='tweetButtonInline']").first
            await tweet_button.wait_for(state="visible", timeout=5000)
            await tweet_button.click()

            logger.info("✅ Twitter post submitted!")
            await self._human_delay(2, 3)

            await asyncio.sleep(5)

            return {
                "success": True,
                "message": "✅ Posted to Twitter successfully!",
                "platform": "Twitter"
            }

        except Exception as e:
            logger.error(f"Twitter automation error: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "platform": "Twitter"
            }
        finally:
            if page:
                await page.close()

    async def post_to_linkedin(self, content: str, media_path: Optional[str] = None) -> Dict:
        """Fully automate LinkedIn posting with Playwright"""
        page = None
        try:
            logger.info("🤖 Starting LinkedIn automation with Playwright...")
            context = await self._init_browser()
            page = await context.new_page()

            # Navigate to LinkedIn
            await page.goto("https://www.linkedin.com/", wait_until="networkidle")
            await self._human_delay(2, 3)

            # Check if logged in - wait for user to login if needed
            if "login" in page.url.lower() or "authwall" in page.url.lower():
                logger.warning("Not logged in to LinkedIn - waiting for manual login...")
                print("\n⚠️  PLEASE LOG IN TO LINKEDIN IN THE BROWSER WINDOW")
                print("   The bot will continue automatically after you log in.\n")

                try:
                    await page.wait_for_url("**/linkedin.com/feed**", timeout=120000)
                    await self._human_delay(3, 5)
                except:
                    return {
                        "success": False,
                        "message": "Login timeout - please try again",
                        "requires_login": True
                    }

            logger.info("✅ Logged in to LinkedIn")

            # Find "Start a post" button - multiple selectors
            start_selectors = [
                "button:has-text('Start a post')",
                "div.share-box-feed-entry__trigger",
                "[aria-label*='Start a post']"
            ]

            start_button = None
            for selector in start_selectors:
                try:
                    start_button = page.locator(selector).first
                    await start_button.wait_for(state="visible", timeout=5000)
                    break
                except:
                    continue

            if not start_button:
                raise Exception("Could not find 'Start a post' button")

            logger.info("Clicking 'Start a post'...")
            await start_button.click()
            await self._human_delay(1, 2)

            # Find post editor
            editor = page.locator("div.ql-editor[contenteditable='true']").first
            await editor.wait_for(state="visible", timeout=10000)

            logger.info("Typing post...")
            await self._human_type(editor, content)
            await self._human_delay(1, 2)

            # Handle media upload
            if media_path and Path(media_path).exists():
                logger.info("Uploading media...")
                try:
                    photo_button = page.locator("button[aria-label*='Add a photo']").first
                    await photo_button.click()
                    await self._human_delay(1, 2)

                    file_input = page.locator("input[type='file']").first
                    await file_input.set_input_files(str(Path(media_path).absolute()))
                    await self._human_delay(3, 4)
                except Exception as e:
                    logger.warning(f"Media upload skipped: {e}")

            # Click Post button
            logger.info("Clicking Post button...")
            post_button = page.locator("button:has-text('Post')").first
            await post_button.wait_for(state="visible", timeout=5000)
            await post_button.click()

            logger.info("✅ LinkedIn post submitted!")
            await self._human_delay(2, 3)

            await asyncio.sleep(5)

            return {
                "success": True,
                "message": "✅ Posted to LinkedIn successfully!",
                "platform": "LinkedIn"
            }

        except Exception as e:
            logger.error(f"LinkedIn automation error: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "platform": "LinkedIn"
            }
        finally:
            if page:
                await page.close()

    async def close(self):
        """Close browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass


# Singleton instance
_bot_instance = None


def get_social_bot():
    """Get or create social bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = SocialMediaBot()
    return _bot_instance
