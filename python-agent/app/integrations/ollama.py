"""
Ollama Integration for Ultimate Coding Agent
Handles communication with Ollama Cloud (Qwen3-coder) and local Ollama instances
"""

import logging
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama API (both cloud and local)"""
    
    def __init__(self):
        """Initialize Ollama client with cloud-first routing"""
        self.ollama_host = settings.ollama_host
        self.ollama_model = settings.ollama_model
        self.ollama_api_key = settings.ollama_api_key
        self.timeout = settings.ollama_timeout
        
        # Determine if using cloud or local
        self.is_cloud = self.ollama_api_key is not None
        
        if self.is_cloud:
            logger.info(f"🌐 Ollama Cloud mode enabled (Model: {self.ollama_model})")
        else:
            logger.info(f"📱 Ollama Local mode (Host: {self.ollama_host}, Model: {self.ollama_model})")
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using Ollama"""
        model_to_use = model or self.ollama_model
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare request
                headers = {}
                if self.is_cloud and self.ollama_api_key:
                    headers["Authorization"] = f"Bearer {self.ollama_api_key.get_secret_value()}"
                
                request_data = {
                    "model": model_to_use,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                }
                
                # Send request
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json=request_data,
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    "Generated text",
                    model=model_to_use,
                    prompt_length=len(prompt),
                    response_length=len(result.get("response", ""))
                )
                
                return result.get("response", "")
        
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Chat with Ollama model"""
        model_to_use = model or self.ollama_model
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {}
                if self.is_cloud and self.ollama_api_key:
                    headers["Authorization"] = f"Bearer {self.ollama_api_key.get_secret_value()}"
                
                request_data = {
                    "model": model_to_use,
                    "messages": messages,
                    "stream": False,
                    **kwargs
                }
                
                response = await client.post(
                    f"{self.ollama_host}/api/chat",
                    json=request_data,
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    "Chat message processed",
                    model=model_to_use,
                    messages=len(messages)
                )
                
                return result.get("message", {}).get("content", "")
        
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise
    
    async def embeddings(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """Generate embeddings using Ollama"""
        model_to_use = model or self.ollama_model
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {}
                if self.is_cloud and self.ollama_api_key:
                    headers["Authorization"] = f"Bearer {self.ollama_api_key.get_secret_value()}"
                
                request_data = {
                    "model": model_to_use,
                    "prompt": text
                }
                
                response = await client.post(
                    f"{self.ollama_host}/api/embeddings",
                    json=request_data,
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result.get("embedding", [])
        
        except Exception as e:
            logger.error(f"Ollama embeddings failed: {e}")
            raise
    
    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {}
                if self.is_cloud and self.ollama_api_key:
                    headers["Authorization"] = f"Bearer {self.ollama_api_key.get_secret_value()}"
                
                response = await client.get(
                    f"{self.ollama_host}/api/tags",
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                models = [model["name"] for model in result.get("models", [])]
                logger.info(f"Available models: {models}")
                
                return models
        
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return [self.ollama_model]
    
    async def health_check(self) -> bool:
        """Check if Ollama is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {}
                if self.is_cloud and self.ollama_api_key:
                    headers["Authorization"] = f"Bearer {self.ollama_api_key.get_secret_value()}"
                
                response = await client.get(
                    f"{self.ollama_host}/",
                    headers=headers
                )
                
                is_healthy = response.status_code == 200
                mode = "cloud" if self.is_cloud else "local"
                
                if is_healthy:
                    logger.info(f"✅ Ollama {mode} is healthy")
                else:
                    logger.warning(f"⚠️ Ollama {mode} returned status {response.status_code}")
                
                return is_healthy
        
        except Exception as e:
            logger.error(f"❌ Ollama health check failed: {e}")
            return False


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
