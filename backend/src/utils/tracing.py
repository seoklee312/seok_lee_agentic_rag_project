"""
Tracing Utility
Request tracing with correlation IDs
"""
import uuid
import time
import logging
from typing import Optional, Dict, Any
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable for trace ID
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class TraceContext:
    """Trace context for request tracking"""
    
    def __init__(self, trace_id: Optional[str] = None, parent_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_id = parent_id
        self.start_time = time.time()
        self.metadata: Dict[str, Any] = {}
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to trace"""
        self.metadata[key] = value
    
    def get_duration(self) -> float:
        """Get duration in seconds"""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            'trace_id': self.trace_id,
            'parent_id': self.parent_id,
            'duration_ms': self.get_duration() * 1000,
            'metadata': self.metadata
        }


class Tracer:
    """Simple tracer for request tracking"""
    
    @staticmethod
    def start_trace(name: str, trace_id: Optional[str] = None) -> TraceContext:
        """Start a new trace"""
        ctx = TraceContext(trace_id=trace_id)
        trace_id_var.set(ctx.trace_id)
        logger.info(f"Started trace: {name} [trace_id={ctx.trace_id}]")
        return ctx
    
    @staticmethod
    def get_current_trace_id() -> Optional[str]:
        """Get current trace ID"""
        return trace_id_var.get()
    
    @staticmethod
    def end_trace(ctx: TraceContext, name: str):
        """End a trace"""
        duration = ctx.get_duration()
        logger.info(f"Ended trace: {name} [trace_id={ctx.trace_id}] duration={duration:.3f}s")
        trace_id_var.set(None)
    
    @staticmethod
    def trace_event(event: str, **metadata):
        """Log a trace event"""
        trace_id = trace_id_var.get()
        logger.info(f"Trace event: {event} [trace_id={trace_id}] {metadata}")


def trace(func):
    """Decorator for tracing function calls"""
    async def wrapper(*args, **kwargs):
        ctx = Tracer.start_trace(func.__name__)
        try:
            result = await func(*args, **kwargs)
            Tracer.end_trace(ctx, func.__name__)
            return result
        except Exception as e:
            ctx.add_metadata('error', str(e))
            Tracer.end_trace(ctx, func.__name__)
            raise
    return wrapper
