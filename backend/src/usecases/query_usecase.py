"""Query use case - orchestrates the complete query processing flow."""
from typing import Dict, Any
from models import Query
from services.query import QueryService
import logging

logger = logging.getLogger(__name__)


class QueryUseCaseError(Exception):
    """Base exception for query use case errors."""
    pass


class QueryValidationError(QueryUseCaseError):
    """Query validation failed."""
    pass


class QueryUseCase:
    """
    Query UseCase - Orchestration layer.
    
    Responsibilities:
    - Input validation
    - Workflow orchestration
    - Response formatting
    - Error handling
    
    Does NOT contain business logic (delegated to QueryService).
    """
    
    def __init__(self, query_service: QueryService):
        """
        Initialize QueryUseCase.
        
        Args:
            query_service: Service containing business logic
        """
        self.query_service = query_service
    
    async def execute(self, query: Query) -> Dict[str, Any]:
        """
        Execute complete query processing flow.
        
        Orchestration steps:
        1. Validate input
        2. Delegate to service
        3. Format response
        4. Handle errors
        
        Args:
            query: Query object with question and context
            
        Returns:
            Complete response with answer, sources, and metadata
            
        Raises:
            QueryValidationError: If query validation fails
            QueryUseCaseError: If processing fails
        """
        try:
            # Step 1: Validate input
            self._validate_query(query)
            
            # Step 2: Delegate to service (business logic)
            result = await self.query_service.process_query(query)
            
            # Step 3: Format response
            return self._format_response(result)
            
        except QueryValidationError:
            raise
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            raise QueryUseCaseError(f"Failed to process query: {str(e)}")
    
    def _validate_query(self, query: Query):
        """
        Validate query input.
        
        Args:
            query: Query object to validate
            
        Raises:
            QueryValidationError: If validation fails
        """
        if not query:
            raise QueryValidationError("Query object is required")
        
        if not query.question or not query.question.strip():
            raise QueryValidationError("Question is required")
        
        if len(query.question) > 1000:
            raise QueryValidationError("Question too long (max 1000 characters)")
        
        logger.debug(f"Query validated: '{query.question[:50]}...'")
    
    def _format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format service result for API response.
        
        Args:
            result: Result from QueryService
            
        Returns:
            Formatted response
        """
        # Ensure required fields
        formatted = {
            'answer': result.get('answer', ''),
            'mode': result.get('mode', 'unknown'),
            'confidence': result.get('confidence', 'MEDIUM'),
            'sources': result.get('sources', []),
            'metadata': result.get('metadata', {}),
            'total_latency_ms': result.get('total_latency_ms', 0)
        }
        
        # Add optional fields
        if 'step_timings' in result:
            formatted['step_timings'] = result['step_timings']
        
        return formatted
