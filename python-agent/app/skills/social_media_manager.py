"""
Enhanced Social Media Manager with Browser Automation
Handles complete workflow: content type → platform selection → automated posting
"""

import asyncio
from typing import Dict, Any, List, Optional
import structlog

from app.core.config import settings
from app.skills.base_skill import BaseSkill, SkillResult
from app.integrations.ollama import get_ollama_client

logger = structlog.get_logger(__name__)


class SocialMediaManager(BaseSkill):
    """Complete social media posting workflow with automation"""

    name = "social_media_manager"
    description = "Post content to social media with browser automation"
    category = "social"

    # Platform configurations
    PLATFORMS = {
        "facebook": {
            "url": "https://www.facebook.com/",
            "name": "Facebook",
            "supports": ["text", "image", "video"],
            "post_button_selector": "div[aria-label='Create a post']",
        },
        "instagram": {
            "url": "https://www.instagram.com/",
            "name": "Instagram",
            "supports": ["image", "video"],
            "requires": "Must upload media",
        },
        "tiktok": {
            "url": "https://www.tiktok.com/upload",
            "name": "TikTok",
            "supports": ["video"],
            "requires": "Video content required",
        },
        "youtube": {
            "url": "https://studio.youtube.com/",
            "name": "YouTube",
            "supports": ["video"],
            "requires": "Video content required",
        },
        "twitter": {
            "url": "https://twitter.com/compose/tweet",
            "name": "Twitter/X",
            "supports": ["text", "image", "video"],
        },
        "linkedin": {
            "url": "https://www.linkedin.com/",
            "name": "LinkedIn",
            "supports": ["text", "image", "video"],
        },
    }

    def __init__(self):
        super().__init__()
        self.ollama = get_ollama_client()

    async def _execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute social media posting workflow"""
        step = params.get("step", "ask_content_type")

        if step == "ask_content_type":
            return await self._ask_content_type()
        elif step == "ask_platform":
            return await self._ask_platform(params)
        elif step == "post_content":
            return await self._post_content(params)
        else:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown step: {step}"
            )

    async def _ask_content_type(self) -> SkillResult:
        """Ask user for content type"""
        message = """📱 <b>Social Media Posting</b>

What type of content do you want to share?

<b>1️⃣ Text Post</b>
Pure text content (status, thoughts, announcements)

<b>2️⃣ Image Post</b>
Photo or graphic with optional caption

<b>3️⃣ Video Post</b>
Video content (short clips, tutorials, vlogs)

Please select your content type:"""

        return SkillResult(
            success=True,
            output=message,
            data={
                "step": "content_type_selection",
                "options": ["text", "image", "video"]
            }
        )

    async def _ask_platform(self, params: Dict[str, Any]) -> SkillResult:
        """Suggest platforms based on content type"""
        content_type = params.get("content_type", "text")

        # Get suitable platforms
        suitable_platforms = []
        for platform_id, config in self.PLATFORMS.items():
            if content_type in config["supports"]:
                suitable_platforms.append({
                    "id": platform_id,
                    "name": config["name"],
                    "url": config["url"]
                })

        # Use AI to refine suggestions
        suggestions = await self._get_ai_platform_suggestions(
            content_type,
            suitable_platforms
        )

        # Format message
        platform_list = "\n".join([
            f"• <b>{p['name']}</b> - {p.get('reason', 'Great for ' + content_type)}"
            for p in suggestions
        ])

        message = f"""🎯 <b>Platform Selection</b>

Content Type: <b>{content_type.upper()}</b>

<b>Recommended Platforms:</b>
{platform_list}

<b>📌 Options:</b>
1. Select one platform
2. Select multiple platforms
3. Post to ALL recommended platforms

You can also attach your {content_type} content now, or do it after platform selection.

Please choose platforms:"""

        return SkillResult(
            success=True,
            output=message,
            data={
                "step": "platform_selection",
                "content_type": content_type,
                "suitable_platforms": suitable_platforms,
                "suggestions": suggestions
            }
        )

    async def _get_ai_platform_suggestions(
        self,
        content_type: str,
        platforms: List[Dict]
    ) -> List[Dict]:
        """Use AI to provide smart platform suggestions"""
        platform_names = [p["name"] for p in platforms]

        prompt = f"""You are a social media expert. Recommend the best platforms for {content_type} content.

Available platforms: {', '.join(platform_names)}

Provide a brief reason (10-15 words) why each platform is good for {content_type} content.

Respond in JSON format:
[
  {{"platform": "Platform Name", "reason": "Brief reason"}},
  ...
]
"""

        try:
            response = await self.ollama.generate(
                prompt=prompt,
                model=settings.ollama_model,
                stream=False
            )

            import json
            # Try to parse AI response
            text = response.get('response', '[]')
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()

            ai_suggestions = json.loads(text)

            # Merge with platform data
            result = []
            for platform in platforms:
                ai_match = next(
                    (s for s in ai_suggestions if platform["name"].lower() in s["platform"].lower()),
                    None
                )
                result.append({
                    **platform,
                    "reason": ai_match["reason"] if ai_match else f"Great for {content_type}"
                })

            return result

        except Exception as e:
            logger.warning(f"AI suggestion failed, using defaults: {e}")
            return [
                {**p, "reason": f"Popular for {content_type} content"}
                for p in platforms
            ]

    async def _post_content(self, params: Dict[str, Any]) -> SkillResult:
        """Post content to selected platforms"""
        platforms = params.get("platforms", [])
        content_type = params.get("content_type", "text")
        text_content = params.get("text", "")
        media_path = params.get("media_path")

        if not platforms:
            return SkillResult(
                success=False,
                output="",
                error="No platforms selected"
            )

        results = []
        for platform_id in platforms:
            result = await self._post_to_platform(
                platform_id,
                content_type,
                text_content,
                media_path
            )
            results.append(result)

        # Format results
        success_count = sum(1 for r in results if r["success"])
        message = f"""✅ <b>Posting Complete</b>

Posted to {success_count}/{len(platforms)} platforms:

"""
        for r in results:
            status = "✅" if r["success"] else "❌"
            message += f"{status} <b>{r['platform']}</b>: {r['message']}\n"

        return SkillResult(
            success=True,
            output=message,
            data={"results": results}
        )

    async def _post_to_platform(
        self,
        platform_id: str,
        content_type: str,
        text: str,
        media_path: Optional[str] = None
    ) -> Dict:
        """Post to a specific platform using FULL automation"""
        platform_config = self.PLATFORMS.get(platform_id)

        if not platform_config:
            return {
                "platform": platform_id,
                "success": False,
                "message": "Unknown platform"
            }

        try:
            # Use full automation bot
            from app.integrations.social_automation_bot import get_social_bot
            bot = get_social_bot()

            logger.info(f"🤖 Starting FULL automation for {platform_config['name']}...")

            # Call platform-specific automation
            if platform_id == "facebook":
                result = await bot.post_to_facebook(text, media_path)
            elif platform_id == "twitter":
                result = await bot.post_to_twitter(text, media_path)
            elif platform_id == "linkedin":
                result = await bot.post_to_linkedin(text, media_path)
            elif platform_id == "instagram":
                # Instagram requires special handling (API or mobile automation)
                result = await self._fallback_browser_open("instagram", text, media_path)
            elif platform_id == "tiktok":
                result = await self._fallback_browser_open("tiktok", text, media_path)
            elif platform_id == "youtube":
                result = await self._fallback_browser_open("youtube", text, media_path)
            else:
                result = {"success": False, "message": "Platform not supported"}

            return {
                "platform": platform_config["name"],
                "success": result.get("success", False),
                "message": result.get("message", "Automation completed")
            }

        except Exception as e:
            logger.error(f"Failed to automate {platform_id}: {e}")
            # Fallback to browser opening
            return await self._fallback_browser_open(platform_id, text, media_path)

    async def _fallback_browser_open(self, platform_id: str, text: str, media_path: Optional[str]) -> Dict:
        """Fallback: Just open browser if full automation fails"""
        platform_config = self.PLATFORMS.get(platform_id)

        try:
            # Copy to clipboard
            clipboard_status = "⚠️ Type manually"
            if text:
                try:
                    import pyperclip
                    pyperclip.copy(text)
                    clipboard_status = "✅ Copied to clipboard"
                except:
                    pass

            # Open browser
            from app.integrations.browser_controller import get_browser_controller
            browser = get_browser_controller()
            result = await browser.open_url(platform_config["url"])

            return {
                "platform": platform_config["name"],
                "success": True,
                "message": f"Browser opened - {clipboard_status} (Manual posting required)"
            }
        except Exception as e:
            return {
                "platform": platform_config["name"],
                "success": False,
                "message": f"Error: {str(e)}"
            }

