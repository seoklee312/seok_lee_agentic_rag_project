"""Domain Detector - Adaptively detects domain using LLM."""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DomainDetector:
    """Adaptively detect domain using LLM - supports new domains."""
    
    def __init__(self, grok_client, domain_manager):
        self.grok_client = grok_client
        self.domain_manager = domain_manager
    
    async def detect_domain(self, query: str) -> Dict[str, Any]:
        """
        Detect domain adaptively with LLM.
        
        Returns:
            {
                'domain': str,
                'is_configured': bool,
                'system_prompt': str
            }
        """
        configured_domains = self.domain_manager.list_available_domains()
        
        prompt = f"""Detect the domain for this query:

Configured domains: {', '.join(configured_domains)}

Query: "{query}"

Rules:
- If query fits a configured domain, respond with domain name
- If query needs a NEW domain, respond with: NEW:<domain_name>

Examples:
- "aspirin side effects" → medical
- "Miranda rights" → legal
- "stock market trends" → NEW:finance
- "Python programming" → NEW:programming

Respond with domain name or NEW:<domain_name>"""
        
        try:
            response = await self.grok_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="grok-3-mini",
                max_tokens=20,
                temperature=0
            )
            
            detected = response['choices'][0]['message']['content'].strip()
            
            # Check if new domain
            if detected.startswith("NEW:"):
                domain_name = detected.split(":", 1)[1].strip()
                logger.info(f"🆕 New domain detected: {domain_name} for '{query[:50]}...'")
                
                return {
                    'domain': domain_name,
                    'is_configured': False,
                    'system_prompt': f"You are a helpful AI assistant specializing in {domain_name}. Provide accurate, well-researched information."
                }
            
            # Check if configured domain
            elif detected in configured_domains:
                logger.info(f"✅ Configured domain: {detected} for '{query[:50]}...'")
                
                domain_obj = self.domain_manager.get_domain(detected)
                return {
                    'domain': detected,
                    'is_configured': True,
                    'system_prompt': domain_obj.get_system_prompt()
                }
            
            # Fallback to general
            else:
                logger.info(f"📝 General query: '{query[:50]}...'")
                return {
                    'domain': 'general',
                    'is_configured': False,
                    'system_prompt': "You are a helpful AI assistant."
                }
        
        except Exception as e:
            logger.warning(f"Domain detection failed: {e}")
            return {
                'domain': 'general',
                'is_configured': False,
                'system_prompt': "You are a helpful AI assistant."
            }
