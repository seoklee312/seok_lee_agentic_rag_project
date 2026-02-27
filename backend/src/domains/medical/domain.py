"""
Medical/Healthcare Domain Implementation
"""
from ..base import BaseDomain
from .tools import DrugInteractionChecker, SymptomAnalyzer
from config.prompts import MEDICAL_SYSTEM_PROMPT


class MedicalDomain(BaseDomain):
    """Medical/Healthcare domain for clinical decision support"""
    
    def _load_tools(self):
        """Load medical-specific tools"""
        self.tools.register('drug_interaction_checker', DrugInteractionChecker())
        self.tools.register('symptom_analyzer', SymptomAnalyzer())
    
    def get_system_prompt(self) -> str:
        """Medical domain system prompt"""
        return MEDICAL_SYSTEM_PROMPT
