"""
Feedback Collection Service
Tracks user feedback for continuous improvement
"""
import json
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects and stores user feedback on query results"""
    
    def __init__(self, storage_path: str = "../faiss_index/user_data/feedback.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.feedback = self._load_feedback()
        logger.info(f"FeedbackCollector initialized with {len(self.feedback)} entries")
    
    def _load_feedback(self) -> List[Dict]:
        """Load feedback from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    feedback = json.load(f)
                    logger.info(f"Loaded {len(feedback)} feedback entries")
                    return feedback
        except Exception as e:
            logger.error(f"Failed to load feedback: {e}")
        return []
    
    def _save_feedback(self):
        """Persist feedback to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.feedback, f, indent=2)
            logger.info(f"Saved {len(self.feedback)} feedback entries")
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
            raise
    
    def add_feedback(
        self,
        query: str,
        rating: int,
        comment: Optional[str] = None,
        query_id: Optional[str] = None
    ) -> Dict:
        """Add user feedback"""
        with self._lock:
            try:
                if rating not in [-1, 1]:
                    raise ValueError("Rating must be -1 (thumbs down) or 1 (thumbs up)")
                
                feedback_entry = {
                    "id": str(uuid.uuid4()),
                    "query_id": query_id or str(uuid.uuid4()),
                    "query": query,
                    "rating": rating,
                    "comment": comment,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                self.feedback.append(feedback_entry)
                self._save_feedback()
                
                logger.info(f"Added feedback: rating={rating}, query='{query[:50]}...'")
                return feedback_entry
            except ValueError as e:
                logger.warning(f"Invalid feedback: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to add feedback: {e}")
                raise ValueError(f"Failed to add feedback: {str(e)}")
    
    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics"""
        with self._lock:
            try:
                if not self.feedback:
                    return {
                        "total": 0,
                        "positive": 0,
                        "negative": 0,
                        "satisfaction_rate": 0.0
                    }
                
                total = len(self.feedback)
                positive = sum(1 for f in self.feedback if f['rating'] == 1)
                negative = sum(1 for f in self.feedback if f['rating'] == -1)
                
                stats = {
                    "total": total,
                    "positive": positive,
                    "negative": negative,
                    "satisfaction_rate": round(positive / total * 100, 2) if total > 0 else 0.0
                }
                
                logger.debug(f"Feedback stats: {stats}")
                return stats
            except Exception as e:
                logger.error(f"Failed to get feedback stats: {e}")
                return {"total": 0, "positive": 0, "negative": 0, "satisfaction_rate": 0.0}
    
    def get_recent_feedback(self, limit: int = 10) -> List[Dict]:
        """Get recent feedback entries"""
        with self._lock:
            try:
                sorted_feedback = sorted(
                    self.feedback,
                    key=lambda x: x['timestamp'],
                    reverse=True
                )
                recent = sorted_feedback[:limit]
                logger.debug(f"Retrieved {len(recent)} recent feedback entries")
                return recent
            except Exception as e:
                logger.error(f"Failed to get recent feedback: {e}")
                return []
    
    def get_feedback_by_rating(self, rating: int, limit: int = 10) -> List[Dict]:
        """Get feedback filtered by rating"""
        with self._lock:
            try:
                if rating not in [-1, 1]:
                    raise ValueError("Rating must be -1 or 1")
                
                filtered = [f for f in self.feedback if f['rating'] == rating]
                filtered.sort(key=lambda x: x['timestamp'], reverse=True)
                
                limited = filtered[:limit]
                logger.info(f"Retrieved {len(limited)} feedback entries with rating={rating}")
                return limited
            except ValueError:
                raise
            except Exception as e:
                logger.error(f"Failed to filter feedback: {e}")
                return []
