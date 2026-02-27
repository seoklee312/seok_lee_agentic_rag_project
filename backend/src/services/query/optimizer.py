"""Query optimization and rewriting service."""
import re
import hashlib
from typing import List, Tuple, Dict, Optional
import logging
from config.prompts import QUERY_UNDERSTANDING_PROMPT, CONVERSATION_SUMMARY_PROMPT

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Optimize queries for better retrieval."""
    
    def __init__(self, llm_service=None, config: Dict = None) -> None:
        self.llm_service = llm_service
        self.abbreviations: Dict[str, str] = {
            'nba': 'National Basketball Association NBA',
            'nfl': 'National Football League NFL',
            'mlb': 'Major League Baseball MLB',
            'nhl': 'National Hockey League NHL',
            'usa': 'United States of America USA',
            'uk': 'United Kingdom UK',
        }
        
        # Config
        config = config or {}
        app_config = config.get('application', {})
        self.understanding_cache_size = app_config.get('understanding_cache_size', 500)
        self.summary_cache_size = app_config.get('summary_cache_size', 100)
        
        # Caches
        self.understanding_cache = {}  # Cache query understanding results
        self.summary_cache = {}  # Cache conversation summaries
        logger.info(f"QueryOptimizer initialized with caching (understanding={self.understanding_cache_size}, summary={self.summary_cache_size})")
    
    def understand_query(self, query: str, history: List = None) -> Dict[str, any]:
        """Use LLM to understand query intent with HyDE and conversation summarization - WITH CACHING."""
        if not self.llm_service:
            return {'is_greeting': False, 'needs_web': True, 'web_query': query, 'rag_query': query, 'hypothetical_answer': '', 'intent': 'unknown', 'web_queries': [query]}
        
        # Check cache first
        cache_key = self._get_cache_key(query, history)
        if cache_key in self.understanding_cache:
            logger.info(f"🎯 Query understanding cache hit for: '{query[:50]}'")
            return self.understanding_cache[cache_key]
        
        # Fast path: detect common patterns without LLM
        query_lower = query.lower()
        
        # Greetings - only keep this simple check
        if query_lower in ['hi', 'hello', 'hey', 'greetings']:
            return {'is_greeting': True, 'needs_web': False, 'web_query': '', 'rag_query': '', 'hypothetical_answer': '', 'intent': 'greeting', 'web_queries': []}
        
        # Use LLM for all other queries - no hardcoded shortcuts
        # Build context with summarization
        context = self._build_context_with_summary(history) if history else ""
        context_str = f"Conversation Context:\n{context}" if context else ""
        
        prompt = QUERY_UNDERSTANDING_PROMPT.format(context=context_str, query=query)

        try:
            response = self.llm_service.generate(prompt, use_routing_model=True)  # Use fast routing model
            import json
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
                # Ensure web_queries exists and limit to 2 for speed
                if 'web_queries' not in result or not result['web_queries']:
                    result['web_queries'] = [result.get('web_query', query)]
                else:
                    result['web_queries'] = result['web_queries'][:2]  # Limit to 2 queries
                result['web_query'] = result['web_queries'][0]  # Primary query
                
                logger.info(f"🔍 Query Understanding:")
                logger.info(f"  Original: '{query}'")
                logger.info(f"  Intent: {result.get('intent')}")
                logger.info(f"  Needs Web: {result.get('needs_web')}")
                logger.info(f"  Web Queries: {result.get('web_queries')}")
                logger.info(f"  RAG Query: '{result.get('rag_query', query)}'")
                if result.get('hypothetical_answer'):
                    logger.info(f"  HyDE Answer: '{result.get('hypothetical_answer')[:100]}...'")
                
                # Cache result
                self._cache_understanding(cache_key, result)
                return result
        except Exception as e:
            logger.warning(f"LLM query understanding failed: {e}")
        
        fallback = {'is_greeting': False, 'needs_web': True, 'web_query': query, 'web_queries': [query], 'rag_query': query, 'hypothetical_answer': '', 'intent': 'question'}
        self._cache_understanding(cache_key, fallback)
        return fallback
    
    def _get_cache_key(self, query: str, history: List = None) -> str:
        """Generate cache key from query and history."""
        # Include last 2 messages from history for context-aware caching
        history_str = ""
        if history and len(history) > 0:
            recent = history[-2:]
            history_str = "|".join([
                f"{(m.role if hasattr(m, 'role') else m.get('role'))}:{(m.content if hasattr(m, 'content') else m.get('content'))[:50]}"
                for m in recent
            ])
        
        key_str = f"{query}|{history_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _cache_understanding(self, key: str, result: Dict):
        """Cache understanding result with size limit."""
        if len(self.understanding_cache) >= self.understanding_cache_size:
            # Remove oldest half
            items = list(self.understanding_cache.items())
            self.understanding_cache = dict(items[len(items)//2:])
            logger.debug(f"Understanding cache cleared to {len(self.understanding_cache)} entries")
        
        self.understanding_cache[key] = result
    
    def _build_context_with_summary(self, history: List) -> str:
        """Build context with summarization for long conversations - WITH CACHING."""
        if not history or len(history) == 0:
            return ""
        
        # If short conversation, use all
        if len(history) <= 6:
            context = ""
            for msg in history[-6:]:
                role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
                content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
                context += f"{role}: {content[:100]}\n"
            return context
        
        # For long conversations: check cache first, then summarize
        summary_key = self._get_summary_cache_key(history[:-3])
        if summary_key in self.summary_cache:
            logger.info("Conversation summary cache hit")
            summary = self.summary_cache[summary_key]
        else:
            try:
                # Summarize messages 0 to -4
                old_messages = history[:-3]
                old_text = "\n".join([
                    f"{(m.role if hasattr(m, 'role') else m.get('role'))}: {(m.content if hasattr(m, 'content') else m.get('content'))[:100]}" 
                    for m in old_messages
                ])
                
                summary_prompt = CONVERSATION_SUMMARY_PROMPT.format(conversation=old_text)
                summary = self.llm_service.generate(summary_prompt) if self.llm_service else "Previous conversation context."
                
                # Cache summary
                self._cache_summary(summary_key, summary)
            except:
                summary = "Previous conversation context."
        
        # Keep last 3 messages detailed
        recent = ""
        for msg in history[-3:]:
            role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            recent += f"{role}: {content[:100]}\n"
        
        return f"Summary: {summary}\n\nRecent:\n{recent}"
    
    def _get_summary_cache_key(self, messages: List) -> str:
        """Generate cache key for conversation summary."""
        msg_str = "|".join([
            f"{(m.role if hasattr(m, 'role') else m.get('role'))}:{(m.content if hasattr(m, 'content') else m.get('content'))[:50]}"
            for m in messages
        ])
        return hashlib.md5(msg_str.encode()).hexdigest()
    
    def _cache_summary(self, key: str, summary: str):
        """Cache conversation summary with size limit."""
        if len(self.summary_cache) >= self.summary_cache_size:
            # Remove oldest half
            items = list(self.summary_cache.items())
            self.summary_cache = dict(items[len(items)//2:])
            logger.debug(f"Summary cache cleared to {len(self.summary_cache)} entries")
        
        self.summary_cache[key] = summary
    
    def _fallback_context(self, history: List) -> str:
        """Fallback: last 3 messages without summary."""
        try:
            context = ""
            for msg in history[-3:]:
                role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
                content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
                context += f"{role}: {content[:100]}\n"
            return context
        except:
            return ""
    
    def expand_abbreviations(self, query: str) -> str:
        """Expand common abbreviations."""
        words: List[str] = query.lower().split()
        expanded: List[str] = []
        
        for word in words:
            clean_word: str = re.sub(r'[^\w]', '', word)
            if clean_word in self.abbreviations:
                expanded.append(self.abbreviations[clean_word])
                logger.info(f"📝 Expanded abbreviation: '{clean_word}' → '{self.abbreviations[clean_word]}'")
            else:
                expanded.append(word)
        
        result = ' '.join(expanded)
        if result != query:
            logger.info(f"📝 Query after abbreviation expansion: '{result}'")
        return result
    
    def is_multi_part_question(self, query: str) -> bool:
        """Detect if query needs decomposition."""
        indicators: List[str] = ['compare', 'difference between', 'vs', 'versus', 'and', 'both']
        query_lower: str = query.lower()
        return any(ind in query_lower for ind in indicators)
    
    def decompose_query(self, query: str) -> List[str]:
        """Break complex query into sub-queries."""
        query_lower: str = query.lower()
        
        # Handle comparison queries
        if 'compare' in query_lower or 'vs' in query_lower or 'versus' in query_lower:
            # Extract entities
            parts: List[str] = re.split(r'\s+(?:vs|versus|and)\s+', query_lower, flags=re.IGNORECASE)
            if len(parts) >= 2:
                base: str = query_lower.split('compare')[-1] if 'compare' in query_lower else ''
                return [f"{part.strip()} {base}".strip() for part in parts[:2]]
        
        # Handle "both X and Y" queries
        if 'both' in query_lower and 'and' in query_lower:
            match = re.search(r'both\s+(.+?)\s+and\s+(.+?)(?:\s|$)', query_lower)
            if match:
                return [match.group(1).strip(), match.group(2).strip()]
        
        return [query]
    
    def optimize(self, query: str) -> Tuple[str, List[str]]:
        """
        Optimize query for better retrieval.
        Returns: (expanded_query, sub_queries)
        """
        logger.info(f"🔧 Query Optimization:")
        logger.info(f"  Input: '{query}'")
        
        # Expand abbreviations
        expanded: str = self.expand_abbreviations(query)
        
        # Check if multi-part
        if self.is_multi_part_question(query):
            sub_queries: List[str] = self.decompose_query(query)
            logger.info(f"  Multi-part detected, decomposed into {len(sub_queries)} sub-queries:")
            for i, sq in enumerate(sub_queries, 1):
                logger.info(f"    {i}. '{sq}'")
            return expanded, sub_queries
        
        logger.info(f"  Output: '{expanded}'")
        return expanded, [expanded]


# Global instance - will be initialized with LLM in app.py
query_optimizer: Optional[QueryOptimizer] = None
