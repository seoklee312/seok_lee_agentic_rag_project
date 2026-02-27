"""
Domain Abstraction Layer
Base class for all domain-specific implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .tools import ToolRegistry


class BaseDomain(ABC):
    """Abstract base class for domain-specific RAG implementations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.domain_name = config.get('domain', {}).get('name', 'unknown')
        self.tools = ToolRegistry()
        self._load_tools()
    
    @abstractmethod
    def _load_tools(self):
        """Load domain-specific tools (implemented by subclasses)"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get domain-specific system prompt"""
        pass
    
    def get_tools(self) -> ToolRegistry:
        """Get domain tools"""
        return self.tools
    
    def get_collection_id(self) -> Optional[str]:
        """Get xAI Collections ID for this domain"""
        return self.config.get('collection_id')
    
    def preprocess_query(self, query: str) -> str:
        """Add domain-specific context to query"""
        from config.prompts import DOMAIN_QUERY_PREFIXES
        prefix = DOMAIN_QUERY_PREFIXES.get(self.domain_name, "")
        return f"{prefix} {query}" if prefix else query
    
    def postprocess_response(self, response: str) -> str:
        """Add domain-specific disclaimer"""
        from config.prompts import DOMAIN_DISCLAIMERS
        disclaimer = DOMAIN_DISCLAIMERS.get(self.domain_name, "")
        
        if disclaimer and "disclaimer" not in response.lower():
            return response + disclaimer
        return response
    
    def get_retrieval_config(self) -> Dict[str, Any]:
        """Get domain-specific retrieval configuration"""
        return self.config.get('retrieval', {})
    
    def get_name(self) -> str:
        """Get domain name"""
        return self.domain_name
