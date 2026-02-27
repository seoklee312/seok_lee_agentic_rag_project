"""Unit tests for config module"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from config import prompts


class TestPrompts(unittest.TestCase):
    """Test prompt templates"""
    
    def test_system_prompt_exists(self):
        """Test SYSTEM_PROMPT is defined"""
        self.assertIsNotNone(prompts.SYSTEM_PROMPT)
        self.assertIsInstance(prompts.SYSTEM_PROMPT, str)
        self.assertGreater(len(prompts.SYSTEM_PROMPT), 0)
    
    def test_chain_of_thought_prompt(self):
        """Test CHAIN_OF_THOUGHT_PROMPT"""
        self.assertIsNotNone(prompts.CHAIN_OF_THOUGHT_PROMPT)
        self.assertIn("step", prompts.CHAIN_OF_THOUGHT_PROMPT.lower())
    
    def test_query_understanding_prompt(self):
        """Test QUERY_UNDERSTANDING_PROMPT"""
        self.assertIsNotNone(prompts.QUERY_UNDERSTANDING_PROMPT)
    
    def test_web_prompts_exist(self):
        """Test web search prompts exist"""
        self.assertIsNotNone(prompts.WEB_QUERY_EXPANSION_PROMPT)
        self.assertIsNotNone(prompts.WEB_QUALITY_GRADING_PROMPT)
        self.assertIsNotNone(prompts.WEB_ANSWER_GENERATION_PROMPT)
    
    def test_extract_confidence(self):
        """Test extract_confidence function"""
        text_high = "This is correct. [Confidence: HIGH]"
        text_medium = "Maybe this works. [Confidence: MEDIUM]"
        text_low = "Not sure. [Confidence: LOW]"
        text_none = "No confidence marker"
        
        self.assertEqual(prompts.extract_confidence(text_high), "HIGH")
        self.assertEqual(prompts.extract_confidence(text_medium), "MEDIUM")
        self.assertEqual(prompts.extract_confidence(text_low), "LOW")
        # Function returns default MEDIUM when no marker found
        self.assertIn(prompts.extract_confidence(text_none), ["MEDIUM", None])


if __name__ == '__main__':
    unittest.main()
