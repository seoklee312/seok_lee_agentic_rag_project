"""
Adaptive retrieval depth based on query complexity
"""
import re
from typing import Dict


class AdaptiveRetrieval:
    """Dynamically adjust retrieval depth based on query characteristics"""
    
    def __init__(self):
        self.base_k = 5
        self.min_k = 3
        self.max_k = 15
    
    def calculate_k(self, query: str, query_understanding: Dict = None) -> int:
        """
        Calculate optimal k based on query complexity
        
        Factors:
        - Query length (longer = more context needed)
        - Question words (multiple questions = more results)
        - Comparison words (vs, compare = more results)
        - Specificity (specific terms = fewer results)
        """
        k = self.base_k
        
        # Factor 1: Query length
        word_count = len(query.split())
        if word_count > 20:
            k += 3  # Long query = more context
        elif word_count > 10:
            k += 2
        elif word_count < 5:
            k -= 1  # Short query = focused
        
        # Factor 2: Multiple questions
        question_words = ['what', 'how', 'why', 'when', 'where', 'who']
        question_count = sum(1 for word in question_words if word in query.lower())
        if question_count > 1:
            k += 2  # Multiple questions = more results
        
        # Factor 3: Comparison queries
        comparison_words = ['compare', 'contrast', 'difference', 'versus', 'vs', 'vs.']
        if any(word in query.lower() for word in comparison_words):
            k += 3  # Comparison = need multiple perspectives
        
        # Factor 4: Specificity (proper nouns, numbers)
        has_proper_nouns = bool(re.search(r'\b[A-Z][a-z]+\b', query))
        has_numbers = bool(re.search(r'\d+', query))
        if has_proper_nouns or has_numbers:
            k -= 1  # Specific query = fewer results needed
        
        # Factor 5: Query understanding (if available)
        if query_understanding:
            intent = query_understanding.get('intent', '')
            if intent == 'how_to':
                k += 2  # How-to needs more examples
            elif intent == 'definition':
                k -= 1  # Definition needs focused answer
        
        # Clamp to min/max
        k = max(self.min_k, min(self.max_k, k))
        
        return k
    
    def get_retrieval_config(self, query: str, query_understanding: Dict = None) -> Dict:
        """Get complete retrieval configuration"""
        k = self.calculate_k(query, query_understanding)
        
        return {
            'top_k': k,
            'reasoning': self._explain_k(query, k),
            'adaptive': True
        }
    
    def _explain_k(self, query: str, k: int) -> str:
        """Explain why this k was chosen"""
        word_count = len(query.split())
        
        if k > 10:
            return f"Complex query ({word_count} words) requires broad context"
        elif k > 7:
            return f"Moderate complexity query needs multiple sources"
        elif k < 5:
            return f"Focused query ({word_count} words) needs precise answer"
        else:
            return f"Standard retrieval depth for typical query"


# Global instance
adaptive_retrieval = AdaptiveRetrieval()
