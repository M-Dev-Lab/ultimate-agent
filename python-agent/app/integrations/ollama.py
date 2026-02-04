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
        """Chat with cloud-first fallback"""
        
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
                return self._extract_response(result)
                
            except Exception as e:
                logger.warning(f"Cloud chat failed: {e}, using local...")
        
        # Fallback to local
        try:
            local_model = model or self.local_model
            data = {
                "model": local_model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
            
            result = await self._call_ollama(self.local_host, data)
            return self._extract_response(result)
            
        except Exception as e:
            logger.error(f"All chat methods failed: {e}")
            raise Exception(f"Unable to get AI response: {e}")
    
    def _extract_response(self, result: Dict) -> str:
        """Extract content from Ollama response"""
        try:
            if isinstance(result, str):
                return result
            
            if "message" in result and isinstance(result["message"], dict):
                return result["message"].get("content", str(result))
            
            if "response" in result:
                return result["response"]
            
            if "output" in result:
                return result["output"]
            
            logger.warning(f"Unexpected Ollama response structure: {result.keys()}")
            return str(result)
            
        except Exception as e:
            logger.error(f"Response extraction failed: {e}")
            return str(result)
    
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
