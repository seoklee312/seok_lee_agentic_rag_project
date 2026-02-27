"""
Centralized Error Classification
Structured error types for the framework
"""
from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Error categories for classification"""
    DOMAIN = "domain"
    API = "api"
    CONFIG = "config"
    VALIDATION = "validation"
    INFRASTRUCTURE = "infrastructure"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FrameworkError(Exception):
    """Base exception for framework errors"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[dict] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
    
    def to_dict(self):
        """Convert to structured dict"""
        return {
            "error": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details
        }


class DomainError(FrameworkError):
    """Domain-specific errors"""
    def __init__(self, message: str, domain: str, **kwargs):
        super().__init__(
            message,
            ErrorCategory.DOMAIN,
            details={"domain": domain, **kwargs}
        )


class APIError(FrameworkError):
    """API-related errors"""
    def __init__(self, message: str, api: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            ErrorCategory.API,
            details={"api": api, "status_code": status_code, **kwargs}
        )


class ConfigError(FrameworkError):
    """Configuration errors"""
    def __init__(self, message: str, config_path: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            ErrorCategory.CONFIG,
            severity=ErrorSeverity.HIGH,
            details={"config_path": config_path, **kwargs}
        )


class ValidationError(FrameworkError):
    """Validation errors"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            ErrorCategory.VALIDATION,
            details={"field": field, **kwargs}
        )
