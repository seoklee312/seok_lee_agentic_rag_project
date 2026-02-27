"""Evaluation package"""
from .evaluator import ModelEvaluator
from .metrics import MetricsCalculator
from .benchmark_data import ALL_QUERIES, MEDICAL_QUERIES, LEGAL_QUERIES

__all__ = ['ModelEvaluator', 'MetricsCalculator', 'ALL_QUERIES', 'MEDICAL_QUERIES', 'LEGAL_QUERIES']
