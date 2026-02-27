"""Intent Classifier - Determines if query is conversational or domain-specific."""
import logging
from typing import Literal

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies query intent using LLM."""
    
    def __init__(self, grok_client):
        self.grok_client = grok_client
    
    async def classify(self, query: str) -> Literal["conversational", "domain_query"]:
        """
        Classify query intent.
        
        Returns:
            "conversational" - Greeting, chitchat, general conversation
            "domain_query" - Needs knowledge retrieval
        """
        prompt = f"""Classify this query intent:

Query: "{query}"

Is this:
A) Conversational (greeting, chitchat, "how are you", "tell me a joke")
B) Domain-specific query (needs knowledge: medical, legal, technical, factual)

Respond with ONLY: conversational OR domain_query"""
        
        try:
            response = await self.grok_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="grok-3-mini",
                max_tokens=10,
                temperature=0
            )
            
            intent = response.get('content', '').strip().lower()
            
            if "conversational" in intent:
                logger.info(f"💬 Conversational query: '{query[:50]}...'")
                return "conversational"
            else:
                logger.info(f"🔍 Domain query: '{query[:50]}...'")
                return "domain_query"
        
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, defaulting to domain_query")
            return "domain_query"
