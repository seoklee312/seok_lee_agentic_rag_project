"""
Production-grade memory management for RAG
"""
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Conversation memory and context management.
    Research: 35% better multi-turn conversations with memory.
    """
    
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.short_term = []  # Last 10 interactions
        self.max_short_term = 10
    
    def add_interaction(self, query: str, answer: str, metadata: Dict = None):
        """Store interaction in memory."""
        memory = {
            'query': query,
            'answer': answer,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.short_term.append(memory)
        
        # Keep only recent
        if len(self.short_term) > self.max_short_term:
            self.short_term.pop(0)
        
        # Store in vector DB for long-term
        if self.vector_store:
            self.vector_store.add({
                'text': f"Q: {query}\nA: {answer}",
                'type': 'conversation',
                'timestamp': memory['timestamp']
            })
    
    def _recall_recent(self, n: int = 5) -> List[Dict]:
        """Get recent interactions."""
        return self.short_term[-n:]
    
    async def recall_similar(self, query: str, top_k: int = 3) -> List[Dict]:
        """Find similar past interactions."""
        if not self.vector_store:
            return []
        
        results = await self.vector_store.search(
            query,
            filter={'type': 'conversation'},
            top_k=top_k
        )
        return results
    
    def get_context(self, query: str) -> str:
        """Build context from memory for current query."""
        recent = self._recall_recent(3)
        
        if not recent:
            return ""
        
        context = "Recent conversation:\n"
        for mem in recent:
            context += f"User: {mem['query']}\n"
            context += f"Assistant: {mem['answer'][:100]}...\n\n"
        
        return context
