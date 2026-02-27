"""Prompt building service for LLM queries."""
from typing import List, Dict, Optional
from config.prompts import (
    SYSTEM_PROMPT, 
    CHAIN_OF_THOUGHT_PROMPT, 
    CONFIDENCE_PROMPT,
    STRUCTURED_OUTPUT_INSTRUCTION,
    LENGTH_PROMPTS
)
from config.constants import (
    MAX_HISTORY_MESSAGES,
    MAX_CONTENT_PREVIEW,
    MAX_DOC_CONTEXT_LENGTH,
    COT_MIN_WORD_COUNT,
    COT_INTENTS
)


class PromptBuilder:
    """Builds prompts for LLM with system instructions and context."""
    
    @staticmethod
    def build_query_prompt(
        question: str,
        web_results: List[Dict] = None,
        rag_context: List[Dict] = None,
        conversation_history: List = None,
        detail_level: str = "normal",
        response_style: str = "natural",
        enable_cot: bool = False
    ) -> str:
        """Build complete prompt for query answering."""
        from datetime import datetime
        
        parts = [SYSTEM_PROMPT]
        
        # Add response style instruction
        if response_style == "factual":
            parts.append("""
**RESPONSE MODE: FACTUAL**
- Use bullet points and structured format
- Cite every single fact with [1], [2], [3]
- Be extremely precise with numbers, dates, names
- Separate facts clearly
- Example format:
  • Fact 1 with citation[1]
  • Fact 2 with citation[2]
  • Context: Additional detail[1]
""")
        else:  # natural
            parts.append("""
**RESPONSE MODE: NATURAL**
- Write in flowing paragraphs
- Conversational and readable
- Still cite sources inline [1], [2], [3]
- Natural transitions between ideas
""")
        
        # Add current date context
        current_date = datetime.now().strftime("%B %d, %Y")
        parts.append(f"\n**Today's Date**: {current_date}")
        
        # Add conversation history
        if conversation_history:
            history_text = ""
            for msg in conversation_history[-MAX_HISTORY_MESSAGES:]:
                role = "User" if msg.role == "user" else "Assistant"
                history_text += f"{role}: {msg.content[:MAX_CONTENT_PREVIEW]}\n"
            parts.append(f"Conversation history:\n{history_text}")
        
        # Add web results with source quality
        if web_results:
            web_text = "Web Sources (current/recent):\n"
            for i, r in enumerate(web_results, 1):
                authority = r.get('authority_score', 3)
                domain = r.get('domain', 'unknown')
                quality_label = "🔥 High" if authority >= 10 else "✓ Medium" if authority >= 7 else "• Standard"
                web_text += f"[{i}] {quality_label} - {domain}\n"
                web_text += f"    Title: {r['title']}\n"
                web_text += f"    Content: {r['snippet']}\n\n"
            parts.append(web_text)
        
        # Add RAG context with dates
        if rag_context:
            doc_text = "Document Database (may be older):\n"
            for i, d in enumerate(rag_context, 1):
                text = d.get('text', d.get('content', ''))[:MAX_DOC_CONTEXT_LENGTH]
                doc_id = d.get('metadata', {}).get('doc_id', 'unknown')
                
                # Extract date from doc_id (format: 2026-02-18T22:14:17_...)
                doc_date = "unknown date"
                if doc_id.startswith('20'):
                    try:
                        doc_date = doc_id[:10]  # Extract YYYY-MM-DD
                    except:
                        pass
                
                doc_text += f"[Doc {i} - {doc_date}]: {text}\n\n"
            parts.append(doc_text)
        
        # Add question
        parts.append(f"Question: {question}")
        
        # Add date awareness instruction for "latest/today" queries
        if any(word in question.lower() for word in ['latest', 'today', 'recent', 'current', 'now']):
            parts.append(f"\nIMPORTANT: User asked for '{question}'. Today is {current_date}. Prioritize web sources over older documents. If documents are outdated, mention their dates and note that web sources may have more current information.")
        
        # Add enhancements
        if enable_cot:
            parts.append(CHAIN_OF_THOUGHT_PROMPT)
        parts.append(LENGTH_PROMPTS.get(detail_level, LENGTH_PROMPTS["normal"]))
        parts.append(STRUCTURED_OUTPUT_INSTRUCTION)
        parts.append(CONFIDENCE_PROMPT)
        
        return "\n\n".join(parts)
    
    @staticmethod
    def should_enable_cot(intent: str, question: str, enable_cot: Optional[bool]) -> bool:
        """Determine if chain-of-thought should be enabled."""
        if enable_cot is not None:
            return enable_cot
        
        # Auto-detect: use CoT for complex queries
        return intent in COT_INTENTS and len(question.split()) > COT_MIN_WORD_COUNT


prompt_builder = PromptBuilder()
