"""Utils package"""
from .errors import (
    FrameworkError,
    DomainError,
    APIError,
    ConfigError,
    ValidationError,
    ErrorCategory,
    ErrorSeverity
)
from .tracing import Tracer, TraceContext, trace

__all__ = [
    'FrameworkError',
    'DomainError',
    'APIError',
    'ConfigError',
    'ValidationError',
    'ErrorCategory',
    'ErrorSeverity',
    'Tracer',
    'TraceContext',
    'trace'
]
