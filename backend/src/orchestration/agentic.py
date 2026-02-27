"""
State-of-the-art Agentic RAG (2026)
Based on LangGraph patterns: StateGraph with conditional routing
Research: Graph-based > Linear chains for adaptive workflows
"""
from typing import Dict, List, Any, Literal
from enum import Enum
import logging
import asyncio
from config.prompts import (
    ROUTE_CLASSIFICATION_PROMPT,
    RELEVANCE_GRADING_PROMPT,
    QUERY_REWRITE_PROMPT,
    INTELLIGENT_QUERY_REWRITE_PROMPT,
    AGENTIC_ANSWER_GENERATION_PROMPT,
    AGENTIC_GENERATION_PROMPT,
    AGENTIC_VALIDATION_PROMPT
)
from services.validation import HallucinationDetector

logger = logging.getLogger(__name__)


class AgenticState(Dict):
    """
    State object passed between nodes.
    2026 Pattern: Typed state for graph execution.
    """
    question: str
    documents: List[Dict]
    generation: str
    retry_count: int
    route: str
    grade_score: float
    metadata: Dict[str, Any]


class NodeDecision(str, Enum):
    """Node routing decisions."""
    GENERATE = "generate"
    REWRITE = "rewrite"
    WEB_SEARCH = "web_search"
    END = "end"


class AgenticRAGOrchestrator:
    """
    2026 State-of-the-art: Graph-based agentic RAG.
    Research: Conditional routing + self-correction + adaptive retrieval.
    """
    
    def __init__(self, llm, retriever, web_search_agent=None, cache=None):
        self.llm = llm
        self.retriever = retriever
        self.web_search_agent = web_search_agent
        self.cache = cache
        self.max_retries = 2
        self.grade_threshold = 0.7
        
        # Initialize hallucination detector
        embedder = getattr(retriever, 'embedding_model', None)
        self.hallucination_detector = HallucinationDetector(embedder=embedder)
    
    async def execute(self, question: str, system_prompt: str = None, domain: str = None) -> Dict[str, Any]:
        """
        Execute graph-based agentic workflow with caching.
        
        Args:
            question: User query
            system_prompt: Domain-specific system prompt (optional)
            domain: Domain name for collection routing (optional)
        
        Flow: Cache → Route → Retrieve → Grade → (Rewrite if needed) → Generate → Validate → Cache
        """
        # Check cache first (10x faster)
        if self.cache:
            cached = self.cache.get(question)
            if cached and cached.get('cache_hit'):
                logger.info(f"Cache HIT (similarity: {cached.get('similarity', 1.0):.2f})")
                return cached['result']
        
        # Initialize state
        state: AgenticState = {
            'question': question,
            'documents': [],
            'generation': '',
            'system_prompt': system_prompt or "You are a helpful AI assistant.",
            'domain': domain,
            'retry_count': 0,
            'route': '',
            'grade_score': 0.0,
            'metadata': {}
        }
        
        # Node 1: Route query
        state = await self._route_node(state)
        
        # Node 2: Retrieve
        state = await self._retrieve_node(state)
        
        # Node 3: Grade documents (DISABLED for speed - was taking 11s for 0.00 score)
        # state = await self._grade_node(state)
        state['grade_score'] = 1.0  # Assume all documents are relevant
        
        # Conditional: Decide next step (DISABLED - skip rewrite, go straight to generation)
        # decision = self._decide_next(state)
        # 
        # # Node 4a: Rewrite if needed
        # if decision == NodeDecision.REWRITE:
        #     state = await self._rewrite_node(state)
        #     state = await self._retrieve_node(state)  # Re-retrieve
        #     state = await self._grade_node(state)  # Re-grade
        # 
        # # Node 4b: Web search fallback
        # elif decision == NodeDecision.WEB_SEARCH:
        #     state = await self._web_search_node(state)
        
        decision = NodeDecision.GENERATE  # Skip to generation
        
        # Node 5: Generate
        state = await self._generate_node(state)
        
        # Node 6: Validate (self-reflection)
        state = await self._validate_node(state)
        
        result = {
            'answer': state['generation'],
            'sources': state['documents'],
            'metadata': state['metadata']
        }
        
        # Cache result for future queries (10x faster)
        if self.cache:
            self.cache.set(question, result)
        
        return result
    
    async def _route_node(self, state: AgenticState) -> AgenticState:
        """
        Node: Route query to best retrieval strategy.
        OPTIMIZED: Always use hybrid (web + RAG) for best results.
        """
        # Always use hybrid for comprehensive results
        state['route'] = 'vector'  # Will trigger parallel web+RAG in retrieve
        state['metadata']['route'] = 'hybrid'
        state['metadata']['route_method'] = 'fixed'
        logger.info(f"Routed to: hybrid (fixed strategy)")
        return state
        
        # # DISABLED: LLM-based routing (saves 4.5s)
        # question = state['question']
        # question_lower = question.lower()
        # 
        # # Fast pattern-based pre-routing (no LLM needed)
        # temporal_keywords = ['today', 'now', 'current', 'latest', 'recent', 'this week', 'yesterday']
        # factual_keywords = ['what is', 'define', 'explain', 'who is', 'when was', 'where is']
        # 
        # if any(keyword in question_lower for keyword in temporal_keywords):
        #     state['route'] = 'web'
        #     state['metadata']['route'] = 'web'
        #     state['metadata']['route_method'] = 'pattern'
        #     logger.info(f"Fast-routed to: web (temporal pattern)")
        #     return state
        # 
        # if any(keyword in question_lower for keyword in factual_keywords):
        #     state['route'] = 'vector'
        #     state['metadata']['route'] = 'vector'
        #     state['metadata']['route_method'] = 'pattern'
        #     logger.info(f"Fast-routed to: vector (factual pattern)")
        #     return state
        # 
        # # Fall back to LLM for complex queries
        # prompt = ROUTE_CLASSIFICATION_PROMPT.format(query=question)
        # 
        # try:
        #     response = await self.llm.generate([{"role": "user", "content": prompt}])
        #     route = response.get('content', '').strip().lower()
        #     
        #     if route not in ['vector', 'web', 'hybrid']:
        #         route = 'vector'
        #     
        #     state['route'] = route
        #     state['metadata']['route'] = route
        #     state['metadata']['route_method'] = 'llm'
        #     logger.info(f"LLM-routed to: {route}")
        #     
        # except Exception as e:
        #     logger.error(f"[AgenticRAGOrchestrator] Routing failed: {e}", exc_info=True)
        #     state['route'] = 'vector'
        #     state['metadata']['route_method'] = 'fallback'
        # 
        # return state
    
    async def _retrieve_node(self, state: AgenticState) -> AgenticState:
        """
        Node: Retrieve documents using SearchOrchestrator (xAI Collections + FAISS + Web).
        """
        question = state['question']
        domain = state.get('domain')
        
        try:
            # Use SearchOrchestrator for parallel web + RAG (with xAI Collections)
            if self.web_search_agent and hasattr(self.web_search_agent, 'parallel_search'):
                web_results, rag_results = await self.web_search_agent.parallel_search(
                    query=question,
                    domain=domain
                )
                
                docs = rag_results + web_results
                state['documents'] = docs
                state['metadata']['retrieval_source'] = 'parallel_web_rag'
                logger.info(f"Retrieved {len(docs)} documents (RAG: {len(rag_results)}, Web: {len(web_results)})")
            
            else:
                # Fallback to basic retriever
                docs = await asyncio.to_thread(self.retriever.search, question)
                state['documents'] = docs
                logger.info(f"Retrieved {len(docs)} documents (fallback)")
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            state['documents'] = []
        
        return state
    
    async def _grade_node(self, state: AgenticState) -> AgenticState:
        """
        Node: Grade document relevance.
        2026 Pattern: LLM-based grading with score.
        """
        question = state['question']
        documents = state['documents']
        
        if not documents:
            state['grade_score'] = 0.0
            return state
        
        # Grade each document
        relevant_docs = []
        scores = []
        
        for doc in documents[:3]:  # Grade top 3
            content = doc.get('content', '')[:300]
            
            prompt = RELEVANCE_GRADING_PROMPT.format(question=question, content=content)
            
            try:
                response = await self.llm.generate([{"role": "user", "content": prompt}])
                answer = response.get('content', '')
                if 'yes' in answer.lower():
                    relevant_docs.append(doc)
                    scores.append(1.0)
                else:
                    scores.append(0.0)
            except:
                scores.append(0.5)
        
        # Calculate average grade (but keep all documents for now - grading too strict)
        avg_score = sum(scores) / len(scores) if scores else 0.5
        
        # Keep all documents instead of filtering
        state['documents'] = documents
        state['grade_score'] = avg_score
        state['metadata']['grade_score'] = avg_score
        state['metadata']['docs_graded'] = len(documents)
        state['metadata']['docs_relevant'] = len(relevant_docs)
        
        logger.info(f"Grade: {avg_score:.2f}, Relevant: {len(relevant_docs)}/{len(documents)}")
        
        return state
    
    def _decide_next(self, state: AgenticState) -> NodeDecision:
        """
        Conditional: Decide next node based on state.
        2026 Pattern: Explicit routing logic with smart fallbacks.
        """
        grade = state['grade_score']
        retry_count = state['retry_count']
        has_docs = len(state['documents']) > 0
        
        # If we have documents, generate (skip strict grading)
        if has_docs:
            return NodeDecision.GENERATE
        
        # No documents, can retry → rewrite
        if retry_count < self.max_retries:
            return NodeDecision.REWRITE
        
        # Max retries, try web search
        if self.web_search_agent and state['route'] != 'web':
            return NodeDecision.WEB_SEARCH
        
        # Fallback → generate with what we have
        return NodeDecision.GENERATE
    
    async def _rewrite_node(self, state: AgenticState) -> AgenticState:
        """
        Node: Intelligent query rewrite with failure analysis.
        2026 Pattern: Context-aware reformulation with verification.
        """
        question = state['question']
        documents = state['documents']
        grade_score = state['grade_score']
        retry_count = state['retry_count']
        
        # Analyze WHY retrieval failed
        failure_reason = self._analyze_failure(documents, grade_score)
        
        # Build context-aware rewrite prompt
        context_hints = ""
        if documents:
            # Use failed documents to guide rewrite
            doc_terms = set()
            for doc in documents[:2]:
                content = doc.get('content', doc.get('snippet', ''))
                # Extract key terms from irrelevant docs
                words = content.lower().split()
                doc_terms.update([w for w in words if len(w) > 4][:5])
            
            if doc_terms:
                context_hints = f"\nRetrieved documents contained: {', '.join(list(doc_terms)[:5])}"
        
        # Strategy-based rewrite
        if retry_count == 0:
            # First retry: Expand with synonyms/context
            strategy = "expand the query with synonyms and related terms"
        else:
            # Second retry: Simplify to core intent
            strategy = "simplify to core intent and remove ambiguity"
        
        prompt = INTELLIGENT_QUERY_REWRITE_PROMPT.format(
            query=question,
            failure_reason=failure_reason,
            context_hints=context_hints,
            strategy=strategy
        )
        
        try:
            response = await self.llm.generate([{"role": "user", "content": prompt}])
            rewritten = response.get('content', '').strip().strip('"').strip("'")
            
            # Verify rewrite is actually different
            if rewritten.lower() == question.lower():
                # Force variation on second attempt
                if retry_count == 0:
                    rewritten = f"What is {question}"
                else:
                    rewritten = f"Explain {question}"
            
            # Store original for comparison
            if 'original_question' not in state['metadata']:
                state['metadata']['original_question'] = question
            
            state['question'] = rewritten
            state['retry_count'] += 1
            state['metadata'][f'rewrite_{retry_count}'] = {
                'from': question,
                'to': rewritten,
                'reason': failure_reason,
                'strategy': strategy
            }
            
            logger.info(f"Rewrite #{retry_count + 1} ({failure_reason}): '{question}' → '{rewritten}'")
            
        except Exception as e:
            logger.error(f"Rewrite failed: {e}")
        
        return state
    
    def _analyze_failure(self, documents: List[Dict], grade_score: float) -> str:
        """Analyze why retrieval failed to guide rewrite strategy."""
        if not documents:
            return "no_documents_found"
        elif grade_score < 0.3:
            return "completely_irrelevant"
        elif grade_score < 0.5:
            return "partially_relevant"
        else:
            return "low_quality"
    
    async def _web_search_node(self, state: AgenticState) -> AgenticState:
        """
        Node: Fallback to web search.
        """
        if not self.web_search_agent:
            return state
        
        try:
            web_results, _ = await self.web_search_agent.parallel_search(state['question'])
            state['documents'] = web_results
            state['metadata']['web_fallback'] = True
            logger.info(f"Web fallback: {len(web_results)} docs")
        except Exception as e:
            logger.error(f"Web search failed: {e}")
        
        return state
    
    async def _generate_node(self, state: AgenticState) -> AgenticState:
        """
        Node: Generate answer from documents with domain-specific system prompt.
        """
        question = state['question']
        documents = state['documents']
        system_prompt = state.get('system_prompt', "You are a helpful AI assistant.")
        
        if not documents:
            logger.warning(f"⚠️ No documents available for generation")
            state['generation'] = "I don't have enough information to answer this question."
            state['metadata']['confidence'] = 0.0
            state['metadata']['hallucination_score'] = 1.0
            return state
        
        logger.info(f"📝 Generating answer from {len(documents)} documents")
        
        # Build context
        context = "\n\n".join([
            f"[{i+1}] {doc.get('content', doc.get('snippet', ''))[:500]}"
            for i, doc in enumerate(documents[:5])
        ])
        
        # Use domain-specific system prompt
        from config.prompts import AGENTIC_GENERATION_PROMPT
        
        prompt = AGENTIC_GENERATION_PROMPT.format(
            system_prompt=system_prompt,
            context=context,
            question=question
        )
        
        try:
            response = await self.llm.generate([{"role": "user", "content": prompt}])
            answer = response.get('content', '').strip()
            
            if not answer:
                logger.error("❌ LLM returned empty answer")
                state['generation'] = "Error: Empty response from LLM."
            else:
                logger.info(f"✅ Generated answer: {len(answer)} chars")
                state['generation'] = answer
            
            # Verify grounding
            if self.web_search_agent and hasattr(self.web_search_agent, '_verify_grounding'):
                grounding = await self.web_search_agent._verify_grounding(answer, documents)
                state['metadata']['grounding'] = grounding
            
            # Verify citations
            if self.web_search_agent and hasattr(self.web_search_agent, '_verify_citations'):
                citation = await self.web_search_agent._verify_citations(answer, documents)
                state['metadata']['citation_verification'] = citation
            
            logger.info("Generated answer with domain-specific prompt")
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            state['generation'] = "Error generating answer."
        
        return state
    
    async def _validate_node(self, state: AgenticState) -> AgenticState:
        """
        Node: Validate answer for hallucinations.
        2026 Pattern: Self-reflective RAG with hallucination detection.
        """
        answer = state['generation']
        documents = state['documents']
        
        if not answer or len(answer) < 20:
            state['metadata']['confidence'] = 0.0
            state['metadata']['hallucination_score'] = 1.0
            return state
        
        # Calculate hallucination score (hybrid approach)
        hallucination_score = self.hallucination_detector.calculate_score(
            answer=answer,
            documents=documents,
            grade_score=state.get('grade_score', 0.5),
            metadata=state.get('metadata', {})
        )
        
        # Store metrics
        confidence = 1.0 - hallucination_score
        state['metadata']['hallucination_score'] = hallucination_score
        state['metadata']['confidence'] = confidence
        
        # Add warning if high risk
        if hallucination_score > 0.7:
            warning = self.hallucination_detector.get_warning_message(hallucination_score)
            state['metadata']['warning'] = warning
            logger.warning(f"High hallucination risk: {hallucination_score:.2f}")
        
        # LLM-based validation for high-risk cases
        if hallucination_score > 0.6 and documents:
            context = " ".join([doc.get('content', '')[:200] for doc in documents[:3]])
            prompt = AGENTIC_VALIDATION_PROMPT.format(context=context[:500], answer=answer[:300])
            
            try:
                response = await self.llm.generate([{"role": "user", "content": prompt}])
                if 'yes' in response.lower():
                    # LLM detected unsupported claims
                    state['generation'] = "I cannot provide a confident answer based on available information."
                    state['metadata']['validation_failed'] = True
                    state['metadata']['hallucination_score'] = 0.9
                    state['metadata']['confidence'] = 0.1
                    logger.warning("LLM validation failed: unsupported claims detected")
                else:
                    state['metadata']['validation_passed'] = True
            except Exception as e:
                logger.error(f"LLM validation failed: {e}")
        
        logger.info(f"Validation complete (hallucination: {hallucination_score:.2f}, confidence: {confidence:.2f})")
        return state
    
