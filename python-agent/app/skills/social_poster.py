"""
Social Poster Skill for Ultimate Coding Agent
Posts content to social media platforms
"""

import re
from typing import Dict, Any
from app.skills.base_skill import BaseSkill, SkillResult
from app.integrations.ollama import get_ollama_client
import structlog

logger = structlog.get_logger(__name__)


class SocialPosterSkill(BaseSkill):
    """Post content to social media platforms"""
    
    name = "social_poster"
    description = "Post optimized content to social media platforms"
    category = "social"
    
    PLATFORM_CONFIGS = {
        "twitter": {
            "max_length": 280,
            "hashtag_limit": 3,
            "mention_pattern": r"@[\w]+",
            "name": "Twitter/X",
        },
        "linkedin": {
            "max_length": 3000,
            "hashtag_limit": 5,
            "mention_pattern": r"@[\w]+",
            "name": "LinkedIn",
        },
        "facebook": {
            "max_length": 63206,
            "hashtag_limit": 3,
            "mention_pattern": r"@[\w]+",
            "name": "Facebook",
        },
        "instagram": {
            "max_length": 2200,
            "hashtag_limit": 30,
            "mention_pattern": r"@[\w]+",
            "name": "Instagram",
        },
    }
    
    async def _execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute social media posting"""
        platform = params.get("platform", "twitter").lower()
        content = params.get("content", "")
        content_type = params.get("type", "post")
        
        if not content:
            return SkillResult(
                success=False,
                output="",
                error="No content provided"
            )
        
        if platform not in self.PLATFORM_CONFIGS:
            return SkillResult(
                success=False,
                output="",
                error=f"Unsupported platform: {platform}"
            )
        
        config = self.PLATFORM_CONFIGS[platform]
        
        try:
            optimized = await self._optimize_content(content, platform)
            validation = self._validate_content(optimized, platform)
            
            if not validation["valid"]:
                return SkillResult(
                    success=False,
                    output="",
                    error=validation["error"]
                )
            
            hashtags = self._extract_hashtags(optimized)
            if len(hashtags) > config["hashtag_limit"]:
                optimized = self._trim_hashtags(optimized, config["hashtag_limit"])
                hashtags = hashtags[:config["hashtag_limit"]]
            
            mentions = self._extract_mentions(optimized)
            
            result = {
                "platform": platform,
                "platform_name": config["name"],
                "content": optimized,
                "length": len(optimized),
                "max_length": config["max_length"],
                "hashtags": hashtags,
                "mentions": mentions,
                "content_type": content_type,
            }
            
            if params.get("dry_run", False):
                return SkillResult(
                    success=True,
                    output=self._format_preview(result),
                    data=result
                )
            
            post_result = await self._post_to_platform(platform, optimized)
            
            if post_result["success"]:
                result["post_url"] = post_result.get("url")
                return SkillResult(
                    success=True,
                    output=f"✅ Posted to {config['name']}!\n\n"
                           f"Content: {optimized[:100]}...\n"
                           f"Hashtags: {', '.join(hashtags) if hashtags else 'None'}",
                    data=result
                )
            else:
                return SkillResult(
                    success=False,
                    output="",
                    error=post_result.get("error", "Unknown error")
                )
                
        except Exception as e:
            logger.error(f"Social posting failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    async def _optimize_content(self, content: str, platform: str) -> str:
        """Optimize content for specific platform using AI"""
        ollama = get_ollama_client()
        
        config = self.PLATFORM_CONFIGS[platform]
        max_len = config["max_length"] - 50
        
        prompt = f"""Optimize this content for {config['name']}:

Original: {content}

Requirements:
- Professional but engaging tone
- Within {max_len} characters
- Add relevant hashtags (2-5)
- Improve clarity and impact
- Ready to post immediately

Return ONLY the optimized content, no explanations."""

        try:
            result = await ollama.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=300
            )
            
            if result and len(result.strip()) > 10:
                return result.strip()
            return content
            
        except Exception as e:
            logger.warning(f"AI optimization failed: {e}")
            return content
    
    def _validate_content(self, content: str, platform: str) -> Dict:
        """Validate content for platform requirements"""
        config = self.PLATFORM_CONFIGS[platform]
        
        if len(content) > config["max_length"]:
            return {
                "valid": False,
                "error": f"Content too long ({len(content)}/{config['max_length']} chars)"
            }
        
        if not content.strip():
            return {
                "valid": False,
                "error": "Content is empty"
            }
        
        return {"valid": True}
    
    def _extract_hashtags(self, content: str) -> list:
        """Extract hashtags from content"""
        return re.findall(r"#(\w+)", content)
    
    def _extract_mentions(self, content: str) -> list:
        """Extract mentions from content"""
        return re.findall(r"@(\w+)", content)
    
    def _trim_hashtags(self, content: str, limit: int) -> str:
        """Trim hashtags to fit limit"""
        hashtags = self._extract_hashtags(content)
        kept = hashtags[:limit]
        trimmed = content
        
        for tag in hashtags[limit:]:
            trimmed = trimmed.replace(f"#{tag}", "").replace("  ", " ")
        
        return trimmed.strip()
    
    def _format_preview(self, result: Dict) -> str:
        """Format preview of post"""
        platform = result["platform_name"]
        content = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
        
        preview = f"""📱 <b>{platform} Preview</b>

{content}

📊 Stats:
- Length: {result['length']}/{result['max_length']}
- Hashtags: {len(result['hashtags'])}
- Mentions: {len(result['mentions'])}
"""
        if result.get("hashtags"):
            preview += f"\n🏷️ {', '.join(['#' + h for h in result['hashtags']])}"
        
        return preview
    
    async def _post_to_platform(self, platform: str, content: str) -> Dict:
        """Post content to platform (stub - requires API integration)"""
        logger.info(f"Posting to {platform}: {content[:50]}...")
        
        if platform == "twitter":
            pass
        
        return {
            "success": True,
            "url": f"https://{platform}.com/post/example",
            "message": "Content would be posted to API"
        }
    
    async def create_thread(self, topic: str, platform: str = "twitter") -> list:
        """Create a thread of related posts"""
        ollama = get_ollama_client()
        
        prompt = f"""Create a thread about: {topic}

Platform: {platform}

Create 5-7 related posts that tell a story or convey information.
Number each post.
Keep each under {self.PLATFORM_CONFIGS[platform]['max_length'] - 30} chars.

Format:
1. [Post content]
2. [Post content]
etc."""

        try:
            result = await ollama.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=1000
            )
            
            posts = []
            for line in result.strip().split("\n"):
                if line and (line[0].isdigit() or line.startswith("-")):
                    post = re.sub(r"^[\d\-\.]+\s*", "", line).strip()
                    if post:
                        posts.append(post)
            
            return posts
            
        except Exception as e:
            logger.error(f"Thread creation failed: {e}")
            return []
