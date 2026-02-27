"""Query suggestions service based on history and popularity."""
import logging
from typing import List, Dict
from collections import Counter
import re

logger = logging.getLogger(__name__)


class QuerySuggestionsService:
    """Generate query suggestions based on patterns and history."""
    
    def __init__(self, cache_service=None):
        self.cache = cache_service
        self.query_history = []
        self.max_history = 1000
        
        # Popular query templates
        self.templates = [
            "What's the latest {topic} news?",
            "Tell me about {topic}",
            "What happened in {topic}?",
            "Compare {topic1} vs {topic2}",
            "Who won the {topic}?",
            "When is the next {topic}?",
        ]
        
        # Common topics
        self.topics = [
            "basketball", "NBA", "Lakers", "Warriors",
            "football", "NFL", "soccer", "sports",
            "news", "today", "latest"
        ]
    
    def record_query(self, query: str) -> None:
        """Record a query for suggestions."""
        if len(self.query_history) >= self.max_history:
            self.query_history.pop(0)
        
        self.query_history.append(query.lower())
        logger.debug(f"Recorded query: '{query[:50]}...'")
    
    def get_suggestions(
        self, 
        partial_query: str = "", 
        limit: int = 5,
        context: List[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get query suggestions.
        
        Args:
            partial_query: Partial query text for autocomplete
            limit: Maximum suggestions to return
            context: Recent queries for context-aware suggestions
            
        Returns:
            List of suggestions with text and reason
        """
        suggestions = []
        
        # 1. Autocomplete from history
        if partial_query:
            history_matches = self._autocomplete_from_history(partial_query, limit)
            suggestions.extend(history_matches)
        
        # 2. Popular queries
        if len(suggestions) < limit:
            popular = self._get_popular_queries(limit - len(suggestions))
            suggestions.extend(popular)
        
        # 3. Context-aware suggestions
        if context and len(suggestions) < limit:
            contextual = self._get_contextual_suggestions(context, limit - len(suggestions))
            suggestions.extend(contextual)
        
        # 4. Template-based suggestions
        if len(suggestions) < limit:
            template_based = self._get_template_suggestions(partial_query, limit - len(suggestions))
            suggestions.extend(template_based)
        
        # Deduplicate and limit
        seen = set()
        unique_suggestions = []
        for sug in suggestions:
            if sug['text'] not in seen:
                seen.add(sug['text'])
                unique_suggestions.append(sug)
                if len(unique_suggestions) >= limit:
                    break
        
        return unique_suggestions
    
    def _autocomplete_from_history(self, partial: str, limit: int) -> List[Dict]:
        """Autocomplete from query history."""
        partial_lower = partial.lower()
        matches = []
        
        for query in reversed(self.query_history):  # Most recent first
            if query.startswith(partial_lower) and query != partial_lower:
                matches.append({
                    'text': query,
                    'reason': 'recent',
                    'score': 1.0
                })
                if len(matches) >= limit:
                    break
        
        return matches
    
    def _get_popular_queries(self, limit: int) -> List[Dict]:
        """Get most popular queries."""
        if not self.query_history:
            return []
        
        # Count query frequency
        counter = Counter(self.query_history)
        popular = counter.most_common(limit)
        
        return [
            {
                'text': query,
                'reason': 'popular',
                'score': count / len(self.query_history)
            }
            for query, count in popular
        ]
    
    def _get_contextual_suggestions(self, context: List[str], limit: int) -> List[Dict]:
        """Get suggestions based on conversation context."""
        if not context:
            return []
        
        suggestions = []
        last_query = context[-1].lower() if context else ""
        
        # Extract topics from last query
        topics = self._extract_topics(last_query)
        
        # Suggest follow-up questions
        follow_ups = [
            f"Tell me more about {topic}"
            for topic in topics[:limit]
        ]
        
        for follow_up in follow_ups:
            suggestions.append({
                'text': follow_up,
                'reason': 'follow-up',
                'score': 0.8
            })
        
        return suggestions[:limit]
    
    def _get_template_suggestions(self, partial: str, limit: int) -> List[Dict]:
        """Generate suggestions from templates."""
        suggestions = []
        
        # If partial query has a topic, use it
        topics = self._extract_topics(partial) if partial else self.topics[:3]
        
        for template in self.templates[:limit]:
            if '{topic}' in template and topics:
                for topic in topics[:2]:
                    suggestions.append({
                        'text': template.format(topic=topic),
                        'reason': 'template',
                        'score': 0.5
                    })
            elif '{topic1}' in template and len(topics) >= 2:
                suggestions.append({
                    'text': template.format(topic1=topics[0], topic2=topics[1]),
                    'reason': 'template',
                    'score': 0.5
                })
        
        return suggestions[:limit]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text."""
        # Simple word extraction (can be improved with NER)
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Filter to known topics or capitalized words
        topics = [w for w in words if w in self.topics or w.istitle()]
        
        return topics[:5]
    
    def get_trending_queries(self, hours: int = 24, limit: int = 10) -> List[Dict]:
        """Get trending queries in the last N hours."""
        # For now, return popular queries
        # In production, filter by timestamp
        return self._get_popular_queries(limit)


# Global instance
query_suggestions_service = QuerySuggestionsService()
