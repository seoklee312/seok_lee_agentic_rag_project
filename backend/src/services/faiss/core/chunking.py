"""
Chunking strategies for text processing
"""
import re
import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)


class TextChunker:
    """Base class for text chunking"""
    
    def chunk(self, text: str) -> List[str]:
        raise NotImplementedError


class FixedChunker(TextChunker):
    """Fixed-size chunking with overlap"""
    
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(self, text: str) -> List[str]:
        if not text.strip():
            return []
        
        words = text.split()
        if not words:
            return []
        
        chunks = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        
        for i in range(0, len(words), step):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if chunk:
                chunks.append(chunk)
            # Stop if we've covered all words
            if i + self.chunk_size >= len(words):
                break
        
        return chunks


class SemanticChunker(TextChunker):
    """Advanced semantic chunking with multiple strategies"""
    
    def __init__(self, embedding_model, threshold: float = 0.5, 
                 max_chunk_size: int = 1000, min_chunk_size: int = 100):
        self.embedding_model = embedding_model
        self.threshold = threshold
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
    
    def chunk(self, text: str) -> List[str]:
        import time
        start_time = time.time()
        
        if not text or not text.strip():
            return []
        
        # Split into sentences with better regex
        sentences = self._split_sentences(text)
        if not sentences:
            return [text]  # Return original as single chunk
        
        if len(sentences) == 1:
            return sentences  # Single sentence, no need to process
        
        logger.debug(f"Split text into {len(sentences)} sentences")
        
        # Encode all sentences
        encode_start = time.time()
        sentence_embeddings = self.embedding_model.encode(sentences)
        encode_time = time.time() - encode_start
        logger.debug(f"Sentence encoding took {encode_time:.3f}s")
        
        # Calculate similarity matrix for better grouping
        similarities = self._calculate_similarities(sentence_embeddings)
        
        # Group sentences using improved algorithm
        chunks = self._group_sentences(sentences, similarities)
        
        # Post-process chunks
        chunks = self._merge_small_chunks(chunks)
        chunks = self._split_large_chunks(chunks)
        
        total_time = time.time() - start_time
        logger.info(f"Semantic chunking: {len(chunks)} chunks from {len(sentences)} sentences in {total_time:.3f}s")
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Better sentence splitting with abbreviation handling"""
        # Handle common abbreviations
        text = text.replace('Dr.', 'Dr<dot>')
        text = text.replace('Mr.', 'Mr<dot>')
        text = text.replace('Mrs.', 'Mrs<dot>')
        text = text.replace('Ms.', 'Ms<dot>')
        text = text.replace('e.g.', 'e<dot>g<dot>')
        text = text.replace('i.e.', 'i<dot>e<dot>')
        text = text.replace('etc.', 'etc<dot>')
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
        
        # Restore abbreviations
        sentences = [s.replace('<dot>', '.') for s in sentences]
        
        # Filter empty sentences
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_similarities(self, embeddings: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity matrix between consecutive sentences"""
        n = len(embeddings)
        similarities = np.zeros(n - 1)
        
        for i in range(n - 1):
            # Cosine similarity between consecutive sentences
            similarities[i] = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
            )
        
        return similarities
    
    def _group_sentences(self, sentences: List[str], similarities: np.ndarray) -> List[str]:
        """Group sentences using similarity threshold with lookahead"""
        chunks = []
        current_chunk = [sentences[0]]
        current_length = len(sentences[0])
        
        for i in range(1, len(sentences)):
            sentence_len = len(sentences[i])
            similarity = similarities[i - 1]
            
            # Check if we should add to current chunk
            should_add = (
                similarity >= self.threshold and
                current_length + sentence_len <= self.max_chunk_size
            )
            
            # Lookahead: check next sentence similarity
            if i < len(sentences) - 1:
                next_similarity = similarities[i]
                # If current is low but next is high, start new chunk
                if similarity < self.threshold and next_similarity >= self.threshold:
                    should_add = False
            
            if should_add:
                current_chunk.append(sentences[i])
                current_length += sentence_len
            else:
                # Start new chunk
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentences[i]]
                current_length = sentence_len
        
        # Add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """Merge chunks that are too small"""
        if not chunks:
            return chunks
        
        merged = []
        i = 0
        
        while i < len(chunks):
            current = chunks[i]
            
            # If chunk is too small and not the last one
            if len(current) < self.min_chunk_size and i < len(chunks) - 1:
                # Merge with next chunk
                current = current + ' ' + chunks[i + 1]
                i += 2
            else:
                i += 1
            
            merged.append(current)
        
        logger.debug(f"Merged small chunks: {len(chunks)} -> {len(merged)}")
        return merged
    
    def _split_large_chunks(self, chunks: List[str]) -> List[str]:
        """Split chunks that are too large"""
        result = []
        
        for chunk in chunks:
            if len(chunk) <= self.max_chunk_size:
                result.append(chunk)
            else:
                # Split by sentences within the chunk
                sentences = self._split_sentences(chunk)
                sub_chunk = []
                current_length = 0
                
                for sentence in sentences:
                    if current_length + len(sentence) > self.max_chunk_size and sub_chunk:
                        result.append(' '.join(sub_chunk))
                        sub_chunk = [sentence]
                        current_length = len(sentence)
                    else:
                        sub_chunk.append(sentence)
                        current_length += len(sentence)
                
                if sub_chunk:
                    result.append(' '.join(sub_chunk))
        
        if len(result) != len(chunks):
            logger.debug(f"Split large chunks: {len(chunks)} -> {len(result)}")
        
        return result
