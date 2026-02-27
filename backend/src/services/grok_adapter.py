"""
LLM Adapter to make Grok client compatible with existing interface
"""
from typing import List, Dict, Any, Optional


class GrokLLMAdapter:
    """
    Adapter to make GrokClient compatible with existing LLM interface
    Expected by QueryOptimizer, AgenticRAGOrchestrator, etc.
    """
    
    def __init__(self, grok_client):
        self.grok_client = grok_client
        self.model_name = "grok"
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response using Grok API
        Compatible with existing LLM interface
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional parameters
        
        Returns:
            Dict with 'content', 'model', 'usage'
        """
        response = await self.grok_client.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Normalize response format
        return {
            'content': response.get('content', ''),
            'model': response.get('model', 'grok'),
            'usage': response.get('usage', {}),
            'finish_reason': response.get('finish_reason'),
            'raw_response': response
        }
    
    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Simple chat interface
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Max tokens
        
        Returns:
            Response text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.get('content', '')
    
    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        return self.grok_client.get_metrics()
