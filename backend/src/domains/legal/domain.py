"""
Legal/Compliance Domain Implementation
"""
from ..base import BaseDomain
from .tools import CitationValidator, PrecedentFinder
from config.prompts import LEGAL_SYSTEM_PROMPT


class LegalDomain(BaseDomain):
    """Legal/Compliance domain for legal research and analysis"""
    
    def _load_tools(self):
        """Load legal-specific tools"""
        self.tools.register('citation_validator', CitationValidator())
        self.tools.register('precedent_finder', PrecedentFinder())
    
    def get_system_prompt(self) -> str:
        """Legal domain system prompt"""
        return LEGAL_SYSTEM_PROMPT
