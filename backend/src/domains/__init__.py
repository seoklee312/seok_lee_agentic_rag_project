"""Domain package"""
from .base import BaseDomain
from .manager import DomainManager
from .medical import MedicalDomain
from .legal import LegalDomain

__all__ = ['BaseDomain', 'DomainManager', 'MedicalDomain', 'LegalDomain']
