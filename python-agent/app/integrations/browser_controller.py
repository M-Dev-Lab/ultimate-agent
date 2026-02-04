"""
Browser Controller for Social Media Posting
Control locally installed browsers for posting to social platforms
"""

import os
import subprocess
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import urllib.parse
import structlog
from app.core.terminal_logger import TerminalActionLogger

from app.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class BrowserResult:
    """Result of a browser operation"""
    success: bool
    operation: str
    message: str
    details: Optional[Dict] = None
    error: Optional[str] = None


class BrowserController:
    """Control local browsers for social media operations"""
    
    def __init__(self):
        self.browser_paths = {
            "chrome": ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"],
            "firefox": ["/usr/bin/firefox"],
            "brave": ["/usr/bin/brave-browser"],
            "edge": ["/usr/bin/microsoft-edge"],
        }
        self._detect_browsers()
    
    def _detect_browsers(self):
        """Detect available browsers"""
        self.available_browsers = {}
        
        for browser, paths in self.browser_paths.items():
            for path in paths:
                if Path(path).exists():
                    self.available_browsers[browser] = path
                    logger.info(f"Found browser: {browser} at {path}")
                    break
        
        logger.info(f"Available browsers: {list(self.available_browsers.keys())}")
    
    async def open_url(self, url: str, browser: str = None) -> BrowserResult:
        """Open a URL in the specified browser"""
        try:
            browser_path = self._get_browser_path(browser)
            
            if not browser_path:
                # Try default xdg-open
                subprocess.Popen(["xdg-open", url], start_new_session=True)
                
                return BrowserResult(
                    success=True,
                    operation="open_url",
                    message=f"🌐 Opened URL in default browser: {url}"
                )
            
            # Open in specific browser
            subprocess.Popen([browser_path, url], start_new_session=True)
            
            browser_name = browser or "detected browser"
            TerminalActionLogger.log_action("Browser Opened", f"{browser_name}: {url[:40]}...")
            return BrowserResult(
                success=True,
                operation="open_url",
                message=f"🌐 Opened {url} in {browser_name}",
                details={"url": url, "browser": browser}
            )
            
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            return BrowserResult(
                success=False,
                operation="open_url",
                message="❌ Failed to open URL",
                error=str(e)
            )
    
    async def post_to_twitter(self, text: str, media_path: str = None) -> BrowserResult:
        """Open Twitter/X compose tweet dialog"""
        safe_text = urllib.parse.quote(text)
        tweet_url = f"https://twitter.com/intent/tweet?text={safe_text}"
        return await self.open_url(tweet_url, "chrome")
    
    async def post_to_linkedin(self, text: str, media_path: str = None) -> BrowserResult:
        """Open LinkedIn share dialog"""
        share_url = f"https://www.linkedin.com/sharing/share-offsite/?url=https://example.com"
        return await self.open_url(share_url, "chrome")
    
    async def post_to_facebook(self, text: str, media_path: str = None) -> BrowserResult:
        """Open Facebook share dialog"""
        safe_text = urllib.parse.quote(text)
        share_url = f"https://www.facebook.com/sharer/sharer.php?u=https://example.com&quote={safe_text}"
        return await self.open_url(share_url, "chrome")
    
    async def post_to_instagram(self, text: str = None, media_path: str = None) -> BrowserResult:
        """Open Instagram (web upload)"""
        return await self.open_url("https://www.instagram.com/", "chrome")
    
    async def post_to_reddit(self, title: str, text: str = None, subreddit: str = None) -> BrowserResult:
        """Open Reddit submit dialog"""
        if subreddit:
            submit_url = f"https://www.reddit.com/r/{subreddit}/submit?title={title.replace(' ', '%20')}"
        else:
            submit_url = f"https://www.reddit.com/submit?title={title.replace(' ', '%20')}"
        return await self.open_url(submit_url, "firefox")
    
    async def post_to_dev_community(self, title: str, text: str, tags: List[str] = None) -> BrowserResult:
        """Open Dev.to write article dialog"""
        url = "https://dev.to/new"
        return await self.open_url(url, "brave")
    
    async def post_to_hashnode(self, title: str, text: str = None) -> BrowserResult:
        """Open Hashnode draft"""
        url = "https://hashnode.com/new"
        return await self.open_url(url, "brave")
    
    async def post_to_medium(self, title: str, text: str = None) -> BrowserResult:
        """Open Medium new story"""
        url = "https://medium.com/new-story"
        return await self.open_url(url, "chrome")
    
    async def post_blog_to_web(self, title: str, content: str, url: str = None) -> BrowserResult:
        """Open web editor for blog post"""
        if url:
            return await self.open_url(url, "brave")
        # Default to Medium
        return await self.post_to_medium(title, content)
    
    async def create_social_post(
        self,
        platform: str,
        text: str,
        media_path: str = None,
        **kwargs
    ) -> BrowserResult:
        """Create a post on specified social platform"""
        platform = platform.lower()
        
        platforms = {
            "twitter": lambda: self.post_to_twitter(text, media_path),
            "x": lambda: self.post_to_twitter(text, media_path),
            "linkedin": lambda: self.post_to_linkedin(text, media_path),
            "facebook": lambda: self.post_to_facebook(text, media_path),
            "instagram": lambda: self.post_to_instagram(text, media_path),
            "reddit": lambda: self.post_to_reddit(kwargs.get("title", text), text, kwargs.get("subreddit")),
            "dev.to": lambda: self.post_to_dev_community(kwargs.get("title", text), text, kwargs.get("tags")),
            "hashnode": lambda: self.post_to_hashnode(kwargs.get("title", text), text),
            "medium": lambda: self.post_to_medium(kwargs.get("title", text), text),
        }
        
        if platform in platforms:
            TerminalActionLogger.log_action("Social Post Initiated", f"Platform: {platform}")
            return await platforms[platform]()
        
        return BrowserResult(
            success=False,
            operation="create_social_post",
            message=f"❌ Unknown platform: {platform}",
            error=f"Supported platforms: {', '.join(platforms.keys())}"
        )
    
    async def list_browsers(self) -> BrowserResult:
        """List available browsers"""
        browsers = list(self.available_browsers.keys())
        
        if not browsers:
            return BrowserResult(
                success=True,
                operation="list_browsers",
                message="🌐 No browsers detected, will use xdg-open",
                details={"browsers": [], "fallback": "xdg-open"}
            )
        
        return BrowserResult(
            success=True,
            operation="list_browsers",
            message=f"🌐 Available browsers: {', '.join(browsers)}",
            details={"browsers": browsers}
        )
    
    async def take_screenshot(self, path: str = None) -> BrowserResult:
        """Take a screenshot using available tools"""
        try:
            # Try using scrot (common on Linux)
            if not path:
                path = f"/home/zeds/Desktop/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            result = subprocess.run(
                ["scrot", path] if await self._command_exists("scrot") else ["import", "-window", "root", path],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return BrowserResult(
                    success=True,
                    operation="take_screenshot",
                    message=f"📸 Screenshot saved: {path}",
                    details={"path": path}
                )
            
            # Fallback: suggest manual screenshot
            return BrowserResult(
                success=False,
                operation="take_screenshot",
                message="❌ Screenshot tool not available",
                error="Install scrot or use manual screenshot"
            )
            
        except Exception as e:
            return BrowserResult(
                success=False,
                operation="take_screenshot",
                message="❌ Failed to take screenshot",
                error=str(e)
            )
    
    async def _command_exists(self, command: str) -> bool:
        """Check if command exists"""
        try:
            subprocess.run(["which", command], capture_output=True, timeout=2)
            return True
        except:
            return False
    
    def _get_browser_path(self, browser: str = None) -> Optional[str]:
        """Get browser executable path with fallback"""
        if not browser:
            # Return first available if no preference
            if self.available_browsers:
                return next(iter(self.available_browsers.values()))
            return None
        
        browser = browser.lower()
        
        # 1. Check detected browsers
        if browser in self.available_browsers:
            return self.available_browsers[browser]
        
        # 2. Try to find in PATH
        try:
            result = subprocess.run(
                ["which", browser],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                path = result.stdout.decode().strip()
                if path:
                    return path
        except:
            pass
        
        # 3. Last fallback: return any available browser
        if self.available_browsers:
            first_found = next(iter(self.available_browsers.keys()))
            logger.warning(f"Browser '{browser}' not found, falling back to {first_found}")
            return self.available_browsers[first_found]
        
        return None
    
    async def post_announcement(
        self,
        title: str,
        content: str,
        platforms: List[str] = None
    ) -> BrowserResult:
        """Post announcement to multiple platforms"""
        if not platforms:
            platforms = ["twitter", "linkedin", "reddit"]
        
        results = []
        for platform in platforms:
            result = await self.create_social_post(platform, f"{title}\n\n{content}")
            results.append(f"{platform}: {'✅' if result.success else '❌'}")
        
        return BrowserResult(
            success=True,
            operation="post_announcement",
            message=f"📢 Announcement opened for:\n" + "\n".join(results),
            details={"platforms": platforms}
        )


# Global browser controller
_browser_controller: Optional[BrowserController] = None


def get_browser_controller() -> BrowserController:
    """Get or create browser controller"""
    global _browser_controller
    if _browser_controller is None:
        _browser_controller = BrowserController()
    return _browser_controller
