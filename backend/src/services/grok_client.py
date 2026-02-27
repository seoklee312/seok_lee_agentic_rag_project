"""
Grok API Client with retry logic, rate limiting, and fallback
"""
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter"""
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until request can be made"""
        async with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            while self.requests and self.requests[0] < now - 60:
                self.requests.popleft()
            
            if len(self.requests) >= self.requests_per_minute:
                # Wait until oldest request expires
                wait_time = 60 - (now - self.requests[0])
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            self.requests.append(now)


class GrokClient:
    """Grok API client with production features"""
    
    def __init__(self, config: Dict[str, Any], bedrock_fallback=None):
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url', 'https://api.x.ai/v1')
        self.models = config.get('models', {})
        self.default_model = self.models.get('default', 'grok-beta')
        self.max_tokens = config.get('max_tokens', 4096)
        self.temperature = config.get('temperature', 0.7)
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1)
        
        # Rate limiting
        rate_limit = config.get('rate_limit', 60)
        self.rate_limiter = RateLimiter(rate_limit)
        
        # Fallback
        self.bedrock_fallback = bedrock_fallback
        
        # Metrics
        self.total_requests = 0
        self.failed_requests = 0
        self.fallback_requests = 0
        
        logger.info(f"GrokClient initialized with model={self.default_model}, rate_limit={rate_limit}/min")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat completion request to Grok API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: grok-beta)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            stream: Enable streaming (not implemented)
            **kwargs: Additional API parameters
        
        Returns:
            Response dict with 'content', 'model', 'usage', etc.
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens
        
        self.total_requests += 1
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = await self._make_request(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response
            
            except Exception as e:
                logger.warning(f"Grok API attempt {attempt + 1}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed - try fallback
                    self.failed_requests += 1
                    return await self._fallback_to_bedrock(messages, temperature, max_tokens)
    
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to Grok API"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Grok API error {response.status}: {error_text}")
                
                data = await response.json()
                
                # Extract response
                choice = data.get('choices', [{}])[0]
                message = choice.get('message', {})
                content = message.get('content', '')
                
                return {
                    'content': content,
                    'model': data.get('model', model),
                    'usage': data.get('usage', {}),
                    'finish_reason': choice.get('finish_reason'),
                    'raw_response': data
                }
    
    async def _fallback_to_bedrock(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Fallback to Bedrock if Grok fails"""
        if not self.bedrock_fallback:
            raise Exception("Grok API failed and no Bedrock fallback configured")
        
        logger.warning("Falling back to Bedrock after Grok failure")
        self.fallback_requests += 1
        
        try:
            # Call Bedrock (assuming it has similar interface)
            response = await self.bedrock_fallback.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Normalize response format
            return {
                'content': response.get('content', ''),
                'model': 'bedrock-fallback',
                'usage': response.get('usage', {}),
                'finish_reason': 'stop',
                'fallback': True
            }
        
        except Exception as e:
            logger.error(f"Bedrock fallback also failed: {e}")
            raise Exception(f"Both Grok and Bedrock failed: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        return {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'fallback_requests': self.fallback_requests,
            'success_rate': (self.total_requests - self.failed_requests) / max(self.total_requests, 1),
            'fallback_rate': self.fallback_requests / max(self.total_requests, 1)
        }
