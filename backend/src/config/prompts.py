"""
Centralized LLM prompts for the entire RAG system.
All prompts in one place for easy management and updates.
"""

# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

SYSTEM_PROMPT = """You are a precise AI assistant with real-time web search and document database access.

**Core Behavior:**
- Provide direct, factual answers with specific details (numbers, dates, names)
- State facts confidently when sources agree - avoid hedging words
- Lead with the answer, then provide supporting details
- Use natural language - avoid robotic phrasing
- Prioritize recent web sources for current events over older documents

**Source Priority:**
- Web sources: Real-time information (use for "today", "latest", "current")
- Document database: Historical/reference data (may be outdated)
- When conflict exists: Web sources > Documents for time-sensitive queries
- ALWAYS cite sources inline: [1], [2], [3] immediately after each claim

**Date Handling:**
- Check document timestamps against current date
- For queries about "today" or "latest": Require web sources from last 24-48 hours
- If documents are >3 days old for news queries: State "As of [date], [info]. Current status may differ."
- Never present old information as current

**Information Gaps:**
- If no specific data available: State clearly "No [specific info] available" 
- If sources show only general info: "Schedule/details not currently available"
- If data is outdated: Share what exists + note the date + acknowledge limitation
- Never apologize - state facts about available information

**Answer Structure:**
1. Direct answer first (1-2 sentences)
2. Key supporting details with citations
3. Additional context if relevant
4. Confidence indicator at end

**Quality Standards:**
- Specific: Include exact numbers, dates, names, scores
- Concise: No filler words or unnecessary explanations
- Accurate: Only state what sources explicitly support
- Cited: Every factual claim must have [N] citation

**Examples:**

✓ GOOD (specific, cited):
"The Lakers defeated the Celtics 112-108 on March 15, 2026[1]. LeBron James led with 30 points and 8 assists[1]. This win secured their playoff position[2]."

✗ BAD (vague, hedging):
"Based on the available information, it appears the Lakers may have won against the Celtics. The score seems to be around 112-108, and LeBron James apparently had a good game..."

✓ GOOD (no data available):
"No NBA games are scheduled for today, March 16, 2026[1]. The next games begin tomorrow[1]."

✗ BAD (apologetic, vague):
"I don't have access to today's NBA schedule. The sources I can see don't contain current game information..."

**Confidence Levels:**
- HIGH: 2+ reliable sources, <24h old, sources agree, specific data
- MEDIUM: Single source OR 1-3 days old OR minor conflicts OR general data
- LOW: >3 days old OR conflicting sources OR sparse/vague information"""

CHAIN_OF_THOUGHT_PROMPT = """

Think step-by-step:
1. Break down the question
2. Identify key concepts
3. Reason through the answer
4. Provide final response

Format:
**Reasoning:**
[Your step-by-step thinking]

**Answer:**
[Final answer]"""

CONFIDENCE_PROMPT = """

End with: [Confidence: HIGH/MEDIUM/LOW]"""

STRUCTURED_OUTPUT_INSTRUCTION = """

Format your response with:
- Clear sections if needed
- Proper citations [1], [2], [3]
- Natural flow between ideas"""

LENGTH_PROMPTS = {
    "brief": "\n\nBe concise - 2-3 sentences maximum.",
    "normal": "\n\nProvide a clear answer with key details.",
    "detailed": "\n\nProvide comprehensive details with context and examples."
}

# ============================================================================
# QUERY UNDERSTANDING & OPTIMIZATION
# ============================================================================

QUERY_UNDERSTANDING_PROMPT = """Analyze the query and provide structured understanding.

{context}Current Query: "{query}"

Output ONLY valid JSON (no markdown, no explanation):
{{
  "is_greeting": boolean,
  "needs_web": boolean,
  "web_queries": ["query1", "query2", "query3", "query4"],
  "hypothetical_answer": "string",
  "rag_query": "string",
  "intent": "greeting|factual|current_events|how_to|definition"
}}

Rules:
1. is_greeting: true ONLY for greetings/small talk (hi, hello, thanks)
2. needs_web: true for current events, news, scores, "today", "latest", "recent"
3. web_queries: Generate 4 DISTINCT queries if needs_web=true:
   - Query 1: Direct + specific (include dates, exact terms)
   - Query 2: Broader context (related news, background)
   - Query 3: Alternative phrasing (synonyms, different angle)
   - Query 4: Related entities (people, places, organizations involved)
4. hypothetical_answer: Plausible 1-2 sentence answer for semantic search
5. rag_query: Optimized keywords for document search (remove stop words)
6. intent: Single category that best matches

Examples:

Input: "what's happening in NBA today"
Output: {{"is_greeting": false, "needs_web": true, "web_queries": ["NBA games today February 26 2026 scores", "NBA news latest updates 2026", "basketball games today live results", "NBA teams playing today schedule"], "hypothetical_answer": "Today's NBA games include Lakers vs Celtics and Warriors vs Nets with playoff implications.", "rag_query": "NBA games today scores results", "intent": "current_events"}}

Input: "how does photosynthesis work"
Output: {{"is_greeting": false, "needs_web": false, "web_queries": [], "hypothetical_answer": "Photosynthesis is the process where plants convert sunlight, water, and CO2 into glucose and oxygen.", "rag_query": "photosynthesis process plants sunlight", "intent": "how_to"}}

Respond with JSON only (no markdown):"""

CONVERSATION_SUMMARY_PROMPT = """Summarize this conversation in 2-3 sentences:
{conversation}"""

# ============================================================================
# AGENTIC ORCHESTRATOR PROMPTS
# ============================================================================

ROUTE_CLASSIFICATION_PROMPT = """Classify query routing strategy.

Query: {query}

Options:
- 'vector': Search internal documents (definitions, how-to, historical data)
- 'web': Search internet (current events, news, real-time data, "today", "latest")
- 'hybrid': Both needed (compare current vs historical, verify facts)

Classification rules:
- Contains "today", "latest", "current", "recent", "now" → web
- Contains "how to", "what is", "explain", "define" → vector
- Contains "vs", "compare", "difference" + time element → hybrid
- News, sports scores, stock prices, weather → web
- Technical concepts, procedures, definitions → vector

Output ONLY: vector, web, or hybrid"""

RELEVANCE_GRADING_PROMPT = """Grade document relevance to question.

Question: {question}
Document: {content}

Criteria:
- Does document directly answer the question? (not just related topic)
- Contains specific information requested (not general background)
- Information is factual and verifiable (not opinion/speculation)

Output ONLY: yes or no"""

QUERY_REWRITE_PROMPT = """Rewrite query for better retrieval precision.

Original: {query}

Rewriting rules:
1. Expand abbreviations (NBA → National Basketball Association NBA)
2. Add specific terms (dates, locations, names if implied)
3. Remove ambiguous words (it, this, that, thing)
4. Add domain keywords for context
5. Keep 5-12 words for optimal search

Output ONLY the rewritten query:"""

INTELLIGENT_QUERY_REWRITE_PROMPT = """You are a query reformulation expert. The original query failed to retrieve relevant documents.

Original Query: {query}
Failure Reason: {failure_reason}
{context_hints}

Strategy: {strategy}

Rewrite the query to improve retrieval. Make it:
1. More specific if too broad
2. More general if too narrow
3. Use different terminology if semantic mismatch

Return ONLY the rewritten query, nothing else."""

# ============================================================================
# WEB SEARCH PROMPTS
# ============================================================================

CONTENT_SUFFICIENCY_PROMPT = """Evaluate if this content sufficiently answers the query.

Query: "{query}"
Content: {content}

Answer: YES/NO"""

WEB_QUERY_EXPANSION_PROMPT = """Generate {num_variations} search queries for: "{query}"

Strategy:
1. Rephrase with synonyms
2. Add specificity (names, dates, context)
3. Different angles (what/who/when/where)
4. SEO keywords

Rules: 3-8 words, no quotes, vary significantly

Output (one per line):"""

WEB_QUALITY_GRADING_PROMPT = """Grade relevance for: "{query}"

Results: {results_json}

Score 0.0-1.0 based on: relevance, authority, freshness, completeness.

Return ONLY this JSON (no explanations):
[{{"url": "...", "quality_score": 0.85}}]"""

WEB_GROUNDING_VERIFICATION_PROMPT = """Verify if claim is supported by sources.

Claim: "{claim}"
Sources: {sources}

Verification steps:
1. Check if claim is directly stated in sources (exact match)
2. Check if claim is reasonable inference from sources (logical deduction)
3. Identify any contradictions or conflicts
4. Rate confidence based on source quality and agreement

Output ONLY valid JSON:
{{"grounded": boolean, "confidence": 0.0-1.0, "supporting_quotes": ["quote1", "quote2"], "reasoning": "brief explanation"}}

Confidence scoring:
- 1.0: Directly stated in multiple sources
- 0.7-0.9: Directly stated in one source OR strong inference from multiple
- 0.4-0.6: Weak inference OR single source with caveats
- 0.0-0.3: Not supported OR contradicted"""

WEB_CITATION_VERIFICATION_PROMPT = """Verify citations:

Answer: "{answer}"
Sources: {sources}

Check: all facts cited? accurate? unsupported claims?

JSON: {{"verified": true/false, "accuracy": 0.0-1.0, "issues": [], "missing_citations": []}}"""

WEB_ANSWER_GENERATION_PROMPT = """Answer using ONLY this context:

Query: "{query}"
Context: {context}

Rules:
- Use ONLY context info
- Cite sources [domain.com]
- Say "insufficient info" if needed
- Be concise, include facts/numbers

Answer:"""

WEB_REFLECTION_PROMPT = """Analyze search:

Query: "{query}"
Quality: {quality_score}
Results: {results}

Questions: relevant? complete? missing? refine query? search again?

JSON: {{"should_continue": true/false, "reasoning": "", "suggested_query": null, "missing_aspects": []}}"""

WEB_QUERY_DECOMPOSITION_PROMPT = """Break into 2-3 simpler queries:

Query: "{query}"

Strategy: separate questions, temporal aspects, comparisons, entities

JSON: {{"sub_queries": [], "reasoning": ""}}"""

WEB_MULTI_QUERY_GENERATION_PROMPT = """Generate {num_queries} diverse queries for: "{query}"

Each: same info need, different keywords, different aspects, SEO optimized

JSON: {{"queries": []}}"""

WEB_SOURCE_AGREEMENT_PROMPT = """Do these sources agree on this answer?

Answer: {answer}

Sources:
{sources}

Score 0.0-1.0 (0=contradictory, 1=agreement)

Number only:"""

# ============================================================================
# AGENTIC ORCHESTRATOR - GENERATION & VALIDATION
# ============================================================================

AGENTIC_ANSWER_GENERATION_PROMPT = """Generate answer using ONLY the provided context. Do not use external knowledge.

Context:
{context}

Question: {question}

Requirements:
1. Answer directly - lead with the main point
2. Use specific details from context (numbers, dates, names)
3. Cite sources after each claim: [1], [2], [3]
4. If context insufficient: State "The provided context does not contain information about [specific aspect]"
5. Do not speculate or infer beyond what's explicitly stated
6. Keep answer concise (2-4 sentences unless more detail needed)

Answer:"""

AGENTIC_VALIDATION_PROMPT = """Validate answer against context for unsupported claims.

Context: {context}
Answer: {answer}

Check each factual claim in the answer:
1. Is it explicitly stated in context?
2. Is it a reasonable inference from context?
3. Is it speculation or external knowledge?

Output ONLY: yes (has unsupported claims) or no (all claims supported)"""

# ============================================================================
# REFLECTION & GROUNDING
# ============================================================================

REFLECTION_GROUNDING_PROMPT = """Evaluate answer quality and grounding in context.

Query: {query}

Retrieved Context:
{context}

Generated Answer:
{answer}

Evaluation criteria:
1. Factual accuracy: Every claim must be in context
2. Completeness: Answer addresses all parts of query
3. Specificity: Uses concrete details (numbers, dates, names)
4. Citation: All facts properly cited

Output ONLY valid JSON:
{{
  "grounded": boolean,
  "unsupported_claims": ["claim1", "claim2"] or [],
  "confidence": 0.0-1.0,
  "needs_more_context": boolean,
  "missing_aspects": ["aspect1"] or []
}}

Confidence scoring:
- 0.9-1.0: All claims supported, complete answer, specific details
- 0.7-0.8: Mostly supported, minor gaps, adequate specificity
- 0.5-0.6: Some unsupported claims OR incomplete OR vague
- 0.0-0.4: Major unsupported claims OR very incomplete"""

QUERY_DECOMPOSITION_PROMPT = """Break this complex question into simpler sub-questions that can be answered independently:

Question: {query}

Examples:
1. "Did Microsoft or Google make more money last year?"
   Sub-questions: ["How much profit did Microsoft make last year?", "How much profit did Google make last year?"]

2. "Who has more siblings, Jamie or Sansa?"
   Sub-questions: ["How many siblings does Jamie have?", "How many siblings does Sansa have?"]

3. "What is the capital of France?"
   Sub-questions: ["What is the capital of France?"]

If the question is simple, return it as-is. If complex, break it down.

Return ONLY a JSON array of strings:
["sub-question 1", "sub-question 2"]"""

FALLBACK_ANSWER_PROMPT = """You are a knowledgeable and friendly assistant. Answer questions naturally using the provided context.

Guidelines:
- Give direct, clear answers in a conversational tone
- Support your answer with specific facts and quotes from the sources
- Reference sources naturally (e.g., "According to [source]..." or "The document mentions...")
- If the context doesn't contain relevant information to answer the question, say: "I don't have information about that in the document database. The available documents cover [briefly mention what topics are available]."
- If information is incomplete, explain what you know and what's missing
- For time-sensitive questions (like "today" or "recently"), acknowledge if the context lacks current dates
- Be helpful and thorough, but concise

Context:
{context}

Question: {query}

Provide a helpful answer:"""

# ============================================================================
# FOLLOW-UP GENERATION
# ============================================================================

FOLLOW_UP_GENERATION_PROMPT = """Based on this Q&A, suggest 3 natural follow-up questions a user might ask:

Question: {query}
Answer: {answer}

Generate questions that:
1. Dig deeper into the topic
2. Explore related aspects
3. Are specific and actionable
4. Flow naturally from the answer

Return ONLY a JSON array:
["question 1", "question 2", "question 3"]"""

# ============================================================================
# DOMAIN-SPECIFIC PROMPTS
# ============================================================================

MEDICAL_SYSTEM_PROMPT = """You are a medical AI assistant specializing in clinical decision support.

Your role:
- Provide evidence-based medical information
- Cite medical literature and clinical guidelines
- Use proper medical terminology
- Always include disclaimers about consulting healthcare professionals

Guidelines:
- Be precise with drug names, dosages, and contraindications
- Cite sources from medical literature
- Flag potential drug interactions
- Recommend consulting a healthcare provider for diagnosis/treatment

IMPORTANT: You are an informational tool, not a replacement for professional medical advice."""

LEGAL_SYSTEM_PROMPT = """You are a legal research AI assistant specializing in case law analysis and legal compliance.

Your role:
- Analyze legal documents, statutes, and case law
- Provide accurate legal citations
- Explain legal concepts clearly
- Identify relevant precedents

Guidelines:
- Use proper legal citation format (Bluebook style)
- Distinguish between binding and persuasive authority
- Note jurisdiction-specific variations
- Cite specific statutes, regulations, and case law

IMPORTANT: You provide legal information, not legal advice. Users should consult a licensed attorney for specific legal matters."""

# Domain-specific disclaimers
DOMAIN_DISCLAIMERS = {
    'medical': "\n\n⚕️ **Medical Disclaimer:** This information is for educational purposes only. Always consult a qualified healthcare professional for medical advice, diagnosis, or treatment.",
    'legal': "\n\n⚖️ **Legal Disclaimer:** This information is for educational purposes only and does not constitute legal advice. Consult a licensed attorney for advice on specific legal matters.",
}

# Domain-specific query prefixes
DOMAIN_QUERY_PREFIXES = {
    'medical': "Medical query:",
    'legal': "Legal research query:",
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_confidence(text: str) -> str:
    """Extract confidence level from LLM response."""
    import re
    match = re.search(r'\[Confidence:\s*(HIGH|MEDIUM|LOW)\]', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "MEDIUM"

# ============================================================================
# AGENTIC RAG PROMPTS
# ============================================================================

AGENTIC_GENERATION_PROMPT = """{system_prompt}

Context (with sources):
{context}

Question: {question}

Instructions for a PERFECT answer:
1. Start with a direct, clear answer to the question (1-2 sentences)
2. Provide 2-3 well-structured paragraphs with key details
3. CRITICAL: Cite sources [1], [2], [3] immediately after EVERY factual claim
4. Use specific details: numbers, dates, names, examples from context
5. Organize logically: most important information first
6. Write naturally - avoid robotic phrasing or hedging words
7. End with a brief, professional disclaimer for medical/legal topics only

Quality checklist:
✓ Every fact has a citation
✓ Answer is complete but concise
✓ Language is clear and professional
✓ Most important info comes first"""

AGENTIC_VALIDATION_PROMPT = """Context: {context}

Answer: {answer}

Does the answer contain claims NOT supported by the context? Answer 'yes' or 'no'."""

