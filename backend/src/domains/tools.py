"""
Tool Registry and Base Classes
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for domain tools"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool"""
        pass
    
    def get_description(self) -> str:
        """Get tool description"""
        return self.__doc__ or f"{self.name} tool"


class ToolRegistry:
    """Registry for domain-specific tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, name: str, tool: BaseTool):
        """Register a tool"""
        self.tools[name] = tool
        logger.info(f"Registered tool: {name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> list:
        """List all registered tools"""
        return list(self.tools.keys())
    
    async def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return await tool.execute(**kwargs)
