"""Unit tests for services.search_prompts module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from config.prompts import SearchPrompts


class TestSearchPrompts(unittest.TestCase):
    
    def test_query_expansion_prompt(self):
        """Test query expansion prompt generation"""
        prompt = SearchPrompts.query_expansion('Lakers score', 2)
        self.assertIn('Lakers score', prompt)
        self.assertIn('2', prompt)
        self.assertIn('search queries', prompt.lower())
    
    def test_quality_grading_prompt(self):
        """Test quality grading prompt generation"""
        prompt = SearchPrompts.quality_grading('Lakers', '{"url": "test"}')
        self.assertIn('Lakers', prompt)
        self.assertIn('url', prompt)
        self.assertIn('quality', prompt.lower())
    
    def test_grounding_verification_prompt(self):
        """Test grounding verification prompt generation"""
        prompt = SearchPrompts.grounding_verification('Lakers won', 'Source text')
        self.assertIn('Lakers won', prompt)
        self.assertIn('Source text', prompt)
        self.assertIn('grounded', prompt.lower())
    
    def test_citation_verification_prompt(self):
        """Test citation verification prompt generation"""
        prompt = SearchPrompts.citation_verification('Answer', 'Sources')
        self.assertIn('Answer', prompt)
        self.assertIn('Sources', prompt)
        self.assertIn('citation', prompt.lower())
    
    def test_answer_generation_prompt(self):
        """Test answer generation prompt generation"""
        prompt = SearchPrompts.answer_generation('Query', 'Context')
        self.assertIn('Query', prompt)
        self.assertIn('Context', prompt)
        self.assertIn('answer', prompt.lower())
    
    def test_reflection_prompt(self):
        """Test reflection prompt generation"""
        prompt = SearchPrompts.reflection('Query', 'Results', 0.8)
        self.assertIn('Query', prompt)
        self.assertIn('Results', prompt)
        self.assertIn('0.8', prompt)
    
    def test_query_decomposition_prompt(self):
        """Test query decomposition prompt generation"""
        prompt = SearchPrompts.query_decomposition('Complex query')
        self.assertIn('Complex query', prompt)
        self.assertIn('sub', prompt.lower())
    
    def test_route_classification_prompt(self):
        """Test route classification prompt generation"""
        prompt = SearchPrompts.route_classification('Test query')
        self.assertIn('Test query', prompt)
        self.assertIn('vector', prompt.lower())
        self.assertIn('web', prompt.lower())
    
    def test_relevance_grading_prompt(self):
        """Test relevance grading prompt generation"""
        prompt = SearchPrompts.relevance_grading('Query', 'Content')
        self.assertIn('Query', prompt)
        self.assertIn('Content', prompt)
        self.assertIn('relevant', prompt.lower())
    
    def test_source_agreement_prompt(self):
        """Test source agreement prompt generation"""
        prompt = SearchPrompts.source_agreement('Answer', 'Sources')
        self.assertIn('Answer', prompt)
        self.assertIn('Sources', prompt)
        self.assertIn('agree', prompt.lower())


if __name__ == '__main__':
    unittest.main()
