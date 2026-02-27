"""
Query Understanding Service
Preprocesses queries with spell correction, expansion, and intent classification
"""
import logging
import re
from typing import Dict, List, Optional
from textblob import TextBlob
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryPreprocessor:
    """Preprocesses and enhances user queries"""
    
    def __init__(self, config: Dict = None):
        self.synonyms = {
            "find": ["search", "locate", "discover", "look for"],
            "explain": ["describe", "clarify", "define", "tell me about"],
            "how": ["what is the way", "what are the steps", "how do I"],
            "why": ["what is the reason", "what causes", "why does"],
            "show": ["display", "present", "give me"],
            "list": ["enumerate", "show all", "what are"]
        }
        
        # Config
        config = config or {}
        app_config = config.get('application', {})
        self.spell_correction_enabled = app_config.get('spell_correction_enabled', True)
        self.spell_correction_threshold = app_config.get('spell_correction_threshold', 0.3)
        self.spell_cache_max_size = app_config.get('spell_cache_size', 1000)
        
        self.spell_cache = {}  # Cache corrections
        logger.info(f"QueryPreprocessor initialized (spell_correction={self.spell_correction_enabled})")
    
    def _transform_temporal_terms(self, query: str) -> str:
        """Transform temporal terms like 'yesterday', 'today' to actual dates."""
        now = datetime.now()
        
        # Map temporal terms to dates
        temporal_map = {
            'today': now.strftime('%B %d, %Y'),
            'tonight': now.strftime('%B %d, %Y'),
            'yesterday': (now - timedelta(days=1)).strftime('%B %d, %Y'),
            'tomorrow': (now + timedelta(days=1)).strftime('%B %d, %Y'),
            'last night': (now - timedelta(days=1)).strftime('%B %d, %Y'),
        }
        
        transformed = query
        for term, date in temporal_map.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(transformed):
                transformed = pattern.sub(f"{term} ({date})", transformed)
                logger.info(f"Transformed temporal term: '{term}' -> '{date}'")
        
        return transformed
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query (lowercase, remove extra spaces)"""
        try:
            normalized = ' '.join(query.strip().split())
            return normalized
        except Exception as e:
            logger.warning(f"Normalization failed: {e}")
            return query
    
    def _has_likely_typos(self, query: str) -> bool:
        """Quick check if query likely has typos without running full correction."""
        # Skip if disabled
        if not self.spell_correction_enabled:
            return False
            
        # Skip very short queries
        if len(query.split()) < 2:
            return False
        
        # Check for common typo patterns
        words = query.lower().split()
        suspicious_count = 0
        
        for word in words:
            # Skip short words, numbers, URLs
            if len(word) <= 3 or word.isdigit() or '.' in word or '@' in word:
                continue
            
            # Check for repeated characters (teh, helllo)
            if re.search(r'(.)\1{2,}', word):
                suspicious_count += 1
            
            # Check for common typo patterns
            if any(pattern in word for pattern in ['teh', 'recieve', 'occured', 'seperate']):
                suspicious_count += 1
        
        # If >30% of words look suspicious, run correction
        return suspicious_count / max(len(words), 1) > self.spell_correction_threshold
    
    def _correct_spelling(self, query: str) -> str:
        """Correct spelling errors in query with caching - ONLY if likely has typos"""
        # Skip if disabled or no likely typos
        if not self.spell_correction_enabled or not self._has_likely_typos(query):
            return query
        
        try:
            # Check cache first
            if query in self.spell_cache:
                logger.debug(f"Spell correction cache hit for '{query[:30]}...'")
                return self.spell_cache[query]
            
            blob = TextBlob(query)
            corrected = str(blob.correct())
            
            # Cache with size limit (LRU-like: clear oldest half when full)
            if len(self.spell_cache) >= self.spell_cache_max_size:
                # Remove oldest half of entries
                items = list(self.spell_cache.items())
                self.spell_cache = dict(items[len(items)//2:])
                logger.debug(f"Spell cache cleared to {len(self.spell_cache)} entries")
            
            self.spell_cache[query] = corrected
            
            if corrected != query:
                logger.info(f"Spell correction: '{query}' -> '{corrected}'")
            
            return corrected
        except Exception as e:
            logger.warning(f"Spell correction failed: {e}")
            return query
    
    def _expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms"""
        try:
            expanded = [query]
            words = query.lower().split()
            
            for word in words:
                if word in self.synonyms:
                    for synonym in self.synonyms[word]:
                        expanded_query = query.lower().replace(word, synonym)
                        expanded.append(expanded_query)
            
            if len(expanded) > 1:
                logger.info(f"Query expanded to {len(expanded)} variations")
            
            return expanded[:3]  # Limit to 3 variations
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return [query]
    
    def _classify_intent(self, query: str) -> str:
        """Classify query intent"""
        try:
            query_lower = query.lower().strip()
            
            # Question patterns
            if query_lower.startswith(("what", "who", "where", "when")):
                intent = "factual"
            elif query_lower.startswith(("how", "can you explain")):
                intent = "procedural"
            elif query_lower.startswith(("why", "what causes")):
                intent = "causal"
            elif "?" in query:
                intent = "question"
            else:
                intent = "statement"
            
            logger.debug(f"Intent classified as '{intent}' for query: '{query[:50]}...'")
            return intent
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "unknown"
    
    def preprocess(self, query: str) -> Dict:
        """Full preprocessing pipeline"""
        try:
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            # Normalize query
            normalized = self._normalize_query(query)
            
            # Spell correction
            corrected = self._correct_spelling(normalized)
            
            # Transform temporal terms (yesterday -> actual date)
            temporal_transformed = self._transform_temporal_terms(corrected)
            
            # Query expansion
            expanded = self._expand_query(temporal_transformed)
            
            # Intent classification
            intent = self._classify_intent(temporal_transformed)
            
            result = {
                "original": query,
                "normalized": normalized,
                "corrected": corrected,
                "temporal_transformed": temporal_transformed,
                "expanded": expanded,
                "intent": intent,
                "was_corrected": corrected != normalized,
                "was_normalized": normalized != query,
                "was_temporal_transformed": temporal_transformed != corrected
            }
            
            logger.info(f"Preprocessed query: intent={intent}, corrected={result['was_corrected']}, temporal={result['was_temporal_transformed']}")
            return result
        except ValueError as e:
            logger.warning(f"Invalid query: {e}")
            raise
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            raise ValueError(f"Failed to preprocess query: {str(e)}")
