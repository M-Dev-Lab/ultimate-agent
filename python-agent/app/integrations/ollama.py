"""
Ollama Integration for Ultimate Coding Agent
Handles cloud-first with automatic fallback to local models
"""

import logging
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama with cloud-first routing and local fallback"""
    
    def __init__(self):
        self.ollama_host = settings.ollama_host
        self.ollama_model = settings.ollama_model
        self.ollama_api_key = settings.ollama_api_key
        self.timeout = settings.ollama_timeout
        
        # Local model (always available)
        self.local_host = "http://localhost:11434"
        self.local_model = "qwen2.5-coder:7b-instruct-q5_K_M"
        
        # Determine mode
        self.is_cloud = self.ollama_api_key is not None
        
        if self.is_cloud:
            logger.info(f"🌐 Ollama Cloud primary (Model: {self.ollama_model})")
            logger.info(f"📱 Local fallback ready ({self.local_model})")
        else:
            logger.info(f"📱 Ollama Local mode (Host: {self.local_host}, Model: {self.local_model})")
    
    async def _call_ollama(self, host: str, data: Dict, headers: Dict = None) -> Dict:
        """Make request to Ollama API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{host}/api/chat",
                json=data,
                headers=headers or {}
            )
            response.raise_for_status()
            return response.json()
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text with cloud-first, fallback to local"""
        
        # Try cloud first if enabled
        if self.is_cloud:
            try:
                headers = {"Authorization": f"Bearer {self.ollama_api_key.get_secret_value()}"}
                data = {
                    "model": model or self.ollama_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    **kwargs
                }
                
                result = await self._call_ollama(self.ollama_host, data, headers)
                content = result.get("message", {}).get("content", "")
                
                logger.info(f"✅ Cloud generation successful", model=model or self.ollama_model)
                return content
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 401, 403):
                    logger.warning(f"⚠️ Cloud quota/rate limit ({e.response.status_code}), falling back to local...")
                else:
                    logger.warning(f"⚠️ Cloud error: {e.response.status_code}, using local...")
            except Exception as e:
                logger.warning(f"⚠️ Cloud failed: {e}, using local...")
        
        # Fallback to local
        return await self._generate_local(prompt, model, **kwargs)
    
    async def _generate_local(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate using local Ollama"""
        try:
            local_model = model or self.local_model
            
            data = {
                "model": local_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                **kwargs
            }
            
            result = await self._call_ollama(self.local_host, data)
            content = result.get("message", {}).get("content", "")
            
            logger.info(f"✅ Local generation successful", model=local_model)
            return content
            
        except Exception as e:
            logger.error(f"❌ Local generation failed: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Chat with cloud-first fallback to local
        FIXED: Robust response parsing for multiple formats
        """
        
        # Try cloud first if configured
        if self.is_cloud:
            try:
                headers = {"Authorization": f"Bearer {self.ollama_api_key.get_secret_value()}"}
                data = {
                    "model": model or self.ollama_model,
                    "messages": messages,
                    "stream": False,
                    **kwargs
                }
                
                result = await self._call_ollama(self.ollama_host, data, headers)
                content = self._extract_response(result)
                
                if content:
                    logger.info(f"✅ Cloud chat success: {len(content)} chars")
                    return content
                else:
                    logger.warning(f"⚠️ No content extracted from cloud response")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 401, 403):
                    logger.warning(f"⚠️ Cloud quota/rate limit ({e.response.status_code}), falling back...")
                else:
                    logger.warning(f"⚠️ Cloud error: {e.response.status_code}, falling back...")
            except Exception as e:
                logger.warning(f"⚠️ Cloud chat failed: {e}, falling back to local...")
        
        # Fallback to local (or primary if cloud disabled)
        return await self._chat_local(messages, model, **kwargs)
    
    async def _chat_local(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate using local Ollama - FIXED RESPONSE PARSING"""
        try:
            local_model = model or self.local_model
            
            data = {
                "model": local_model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
            
            result = await self._call_ollama(self.local_host, data)
            content = self._extract_response(result)
            
            if not content:
                logger.error(f"❌ No content in local response: {result}")
                raise Exception("Local Ollama returned empty response")
            
            logger.info(f"✅ Local chat success: {len(content)} chars")
            return content
            
        except Exception as e:
            logger.error(f"❌ Local chat failed: {e}")
            raise Exception(f"Unable to get AI response: {e}")
    
    def _extract_response(self, result: Dict) -> str:
        """
        Extract content from Ollama response
        Handles multiple response formats from different Ollama endpoints
        
        Formats supported:
        1. Chat endpoint: {"message": {"content": "..."}}
        2. Generate endpoint: {"response": "..."}
        3. Alternative: {"output": "..."}
        4. Streaming format remnant: {"text": "..."}
        """
        try:
            # Handle string responses (shouldn't happen, but be safe)
            if isinstance(result, str):
                return result.strip()
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected response type: {type(result)}")
                return str(result)
            
            # Format 1: Chat endpoint response (most common)
            if "message" in result:
                message = result["message"]
                if isinstance(message, dict):
                    content = message.get("content")
                    if content:
                        return content.strip()
            
            # Format 2: Generate endpoint response
            if "response" in result:
                response = result["response"]
                if isinstance(response, str):
                    return response.strip()
            
            # Format 3: Alternative output field
            if "output" in result:
                output = result["output"]
                if isinstance(output, str):
                    return output.strip()
            
            # Format 4: Text field (fallback)
            if "text" in result:
                text = result["text"]
                if isinstance(text, str):
                    return text.strip()
            
            # Format 5: Choices array (OpenAI-compatible)
            if "choices" in result and isinstance(result["choices"], list):
                for choice in result["choices"]:
                    if isinstance(choice, dict):
                        # Try message.content first
                        if "message" in choice and "content" in choice["message"]:
                            return choice["message"]["content"].strip()
                        # Try text field
                        if "text" in choice:
                            return choice["text"].strip()
            
            # If we get here, log what we received for debugging
            logger.warning(f"Could not extract response from: {list(result.keys())}")
            logger.debug(f"Full response: {result}")
            
            # Return empty string instead of None
            return ""
            
        except Exception as e:
            logger.error(f"Response extraction exception: {e}, full result: {result}")
            return ""
    
    async def embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generate embeddings"""
        local_model = model or settings.get("embedding_model", "nomic-embed-text")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.local_host}/api/embeddings",
                    json={"model": local_model, "prompt": text}
                )
                response.raise_for_status()
                return response.json().get("embedding", [])
        except Exception as e:
            logger.error(f"Embeddings failed: {e}")
            return []
    
    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Check local first
                response = await client.get(f"{self.local_host}/api/tags")
                response.raise_for_status()
                result = response.json()
                return [m["name"] for m in result.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check both cloud and local health"""
        result = {"cloud": False, "local": False, "primary": None}
        
        # Check local
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.local_host}/api/tags")
                if response.status_code == 200:
                    result["local"] = True
                    result["models"] = [m["name"] for m in response.json().get("models", [])]
        except Exception:
            pass
        
        # Check cloud if configured
        if self.is_cloud:
            try:
                headers = {"Authorization": f"Bearer {self.ollama_api_key.get_secret_value()}"}
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(
                        f"{self.ollama_host}/api/tags",
                        headers=headers
                    )
                    if response.status_code == 200:
                        result["cloud"] = True
            except Exception:
                pass
            
            result["primary"] = "cloud" if result["cloud"] else "local"
        else:
            result["primary"] = "local" if result["local"] else None
        
        logger.info(f"Health check: {result}")
        return result


_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
