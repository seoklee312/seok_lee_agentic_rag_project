"""
Benchmark test sets for model evaluation
Covers: factual, reasoning, long-context, edge-case, ambiguous, creative queries
"""

MEDICAL_QUERIES = [
    # Factual queries
    {
        "query": "What are the contraindications for aspirin?",
        "expected_keywords": ["bleeding", "ulcer", "allergy", "children", "reye"],
        "domain": "medical",
        "type": "factual"
    },
    {
        "query": "Explain the mechanism of action of ACE inhibitors",
        "expected_keywords": ["angiotensin", "blood pressure", "enzyme", "vasodilation"],
        "domain": "medical",
        "type": "factual"
    },
    {
        "query": "What are the symptoms of type 2 diabetes?",
        "expected_keywords": ["thirst", "urination", "fatigue", "glucose", "insulin"],
        "domain": "medical",
        "type": "factual"
    },
    {
        "query": "How does metformin work?",
        "expected_keywords": ["glucose", "insulin", "liver", "diabetes"],
        "domain": "medical",
        "type": "factual"
    },
    {
        "query": "What are the side effects of statins?",
        "expected_keywords": ["muscle", "pain", "liver", "cholesterol"],
        "domain": "medical",
        "type": "factual"
    },
    
    # Reasoning queries
    {
        "query": "A patient takes warfarin and wants to start aspirin. What are the risks and what should be monitored?",
        "expected_keywords": ["bleeding", "interaction", "INR", "monitoring", "risk"],
        "domain": "medical",
        "type": "reasoning"
    },
    {
        "query": "Why would a doctor prescribe both a beta-blocker and an ACE inhibitor for heart failure?",
        "expected_keywords": ["synergistic", "mortality", "remodeling", "combination"],
        "domain": "medical",
        "type": "reasoning"
    },
    
    # Long-context queries
    {
        "query": "Compare and contrast the treatment approaches for type 1 diabetes versus type 2 diabetes, including medication options, lifestyle modifications, monitoring requirements, and potential complications for each type.",
        "expected_keywords": ["insulin", "metformin", "autoimmune", "lifestyle", "complications"],
        "domain": "medical",
        "type": "long-context"
    },
    
    # Edge cases
    {
        "query": "Can aspirin be used in pediatric patients?",
        "expected_keywords": ["reye", "syndrome", "avoid", "children", "risk"],
        "domain": "medical",
        "type": "edge-case"
    },
    {
        "query": "What happens if someone takes 10 times the normal dose of metformin?",
        "expected_keywords": ["overdose", "lactic acidosis", "emergency", "toxicity"],
        "domain": "medical",
        "type": "edge-case"
    },
    
    # Ambiguous queries
    {
        "query": "Is it safe to take aspirin?",
        "expected_keywords": ["depends", "contraindications", "individual", "consult"],
        "domain": "medical",
        "type": "ambiguous"
    },
    
    # Creative queries
    {
        "query": "Explain how ACE inhibitors work using a simple analogy",
        "expected_keywords": ["analogy", "pressure", "valve", "flow"],
        "domain": "medical",
        "type": "creative"
    }
]

LEGAL_QUERIES = [
    # Factual queries
    {
        "query": "What is the doctrine of stare decisis?",
        "expected_keywords": ["precedent", "binding", "court", "decision"],
        "domain": "legal",
        "type": "factual"
    },
    {
        "query": "Explain the difference between civil and criminal law",
        "expected_keywords": ["plaintiff", "defendant", "prosecution", "damages", "punishment"],
        "domain": "legal",
        "type": "factual"
    },
    {
        "query": "What is the burden of proof in criminal cases?",
        "expected_keywords": ["reasonable doubt", "beyond", "prosecution", "prove"],
        "domain": "legal",
        "type": "factual"
    },
    {
        "query": "What are the elements of a valid contract?",
        "expected_keywords": ["offer", "acceptance", "consideration", "capacity"],
        "domain": "legal",
        "type": "factual"
    },
    {
        "query": "What is the Miranda warning?",
        "expected_keywords": ["rights", "silence", "attorney", "police", "custody"],
        "domain": "legal",
        "type": "factual"
    },
    
    # Reasoning queries
    {
        "query": "If a contract was signed under duress, is it enforceable? Explain the legal reasoning.",
        "expected_keywords": ["void", "voidable", "duress", "consent", "invalid"],
        "domain": "legal",
        "type": "reasoning"
    },
    {
        "query": "How does the exclusionary rule protect Fourth Amendment rights?",
        "expected_keywords": ["evidence", "suppression", "illegal search", "deterrent"],
        "domain": "legal",
        "type": "reasoning"
    },
    
    # Long-context queries
    {
        "query": "Trace the evolution of Miranda rights from the original Miranda v. Arizona decision through subsequent Supreme Court cases that have modified or clarified the rule, including the practical implications for law enforcement.",
        "expected_keywords": ["miranda", "evolution", "supreme court", "law enforcement", "rights"],
        "domain": "legal",
        "type": "long-context"
    },
    
    # Edge cases
    {
        "query": "Can a contract be valid if one party is a minor?",
        "expected_keywords": ["minor", "voidable", "capacity", "age", "disaffirm"],
        "domain": "legal",
        "type": "edge-case"
    },
    {
        "query": "What happens if police forget to read Miranda rights?",
        "expected_keywords": ["suppression", "exclusion", "statements", "inadmissible"],
        "domain": "legal",
        "type": "edge-case"
    },
    
    # Ambiguous queries
    {
        "query": "Is this contract legal?",
        "expected_keywords": ["depends", "terms", "jurisdiction", "review", "attorney"],
        "domain": "legal",
        "type": "ambiguous"
    },
    
    # Creative queries
    {
        "query": "Explain stare decisis using a real-world analogy",
        "expected_keywords": ["analogy", "precedent", "consistency", "follow"],
        "domain": "legal",
        "type": "creative"
    }
]

ALL_QUERIES = MEDICAL_QUERIES + LEGAL_QUERIES

# Query type distribution
QUERY_TYPES = {
    "factual": [q for q in ALL_QUERIES if q.get("type") == "factual"],
    "reasoning": [q for q in ALL_QUERIES if q.get("type") == "reasoning"],
    "long-context": [q for q in ALL_QUERIES if q.get("type") == "long-context"],
    "edge-case": [q for q in ALL_QUERIES if q.get("type") == "edge-case"],
    "ambiguous": [q for q in ALL_QUERIES if q.get("type") == "ambiguous"],
    "creative": [q for q in ALL_QUERIES if q.get("type") == "creative"]
}
