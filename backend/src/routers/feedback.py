"""
Feedback endpoints router
"""
from fastapi import APIRouter, Request, HTTPException
from models import Feedback
from typing import Optional
import logging

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)


@router.post("")
async def submit_feedback(request: Request, feedback: Feedback):
    """Submit user feedback"""
    try:
        logger.info(f"Submitting feedback: rating={feedback.rating}")
        
        feedback_collector = request.app.state.feedback_collector
        metrics = request.app.state.metrics
        
        result = feedback_collector.add_feedback(
            feedback.query,
            feedback.rating,
            feedback.comment,
            feedback.query_id
        )
        metrics['feedback_submitted'] += 1
        
        # Record in metrics service
        if hasattr(request.app.state, 'metrics_service'):
            request.app.state.metrics_service.record_feedback(
                is_positive=(feedback.rating >= 4)
            )
        
        logger.info(f"Feedback submitted: {result['id']}")
        return {"status": "submitted", "feedback": result}
    except ValueError as e:
        logger.warning(f"Invalid feedback: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_feedback_stats(request: Request):
    """Get feedback statistics"""
    try:
        feedback_collector = request.app.state.feedback_collector
        stats = feedback_collector.get_feedback_stats()
        logger.info(f"Feedback stats retrieved: {stats['total']} entries")
        return stats
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent")
async def get_recent_feedback(limit: int = 10):
    """Get recent feedback entries"""
    try:
        feedback = feedback_collector.get_recent_feedback(limit)
        logger.info(f"Retrieved {len(feedback)} recent feedback entries")
        return {"feedback": feedback, "count": len(feedback)}
    except Exception as e:
        logger.error(f"Failed to get recent feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/by-rating")
async def get_feedback_by_rating(rating: int, limit: int = 10):
    """Get feedback filtered by rating (-1 or 1)"""
    try:
        feedback = feedback_collector.get_feedback_by_rating(rating, limit)
        logger.info(f"Retrieved {len(feedback)} feedback entries with rating={rating}")
        return {"rating": rating, "feedback": feedback, "count": len(feedback)}
    except ValueError as e:
        logger.warning(f"Invalid rating: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get feedback by rating: {e}")
        raise HTTPException(status_code=500, detail=str(e))
