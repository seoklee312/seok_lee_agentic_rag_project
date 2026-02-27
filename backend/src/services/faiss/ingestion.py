"""
Document ingestion service
"""
import os
import logging
from typing import List, Dict
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Service for ingesting documents from various sources"""
    
    def __init__(self, chunker):
        self.chunker = chunker
    
    def ingest_from_directory(self, directory: str) -> List[Dict]:
        """Ingest all text files from a directory with metadata"""
        if not os.path.exists(directory):
            raise ValueError(f"Directory not found: {directory}")
        
        documents = []
        txt_files = [f for f in os.listdir(directory) if f.endswith('.txt')]
        
        if not txt_files:
            raise ValueError(f"No .txt files found in {directory}")
        
        logger.info(f"Found {len(txt_files)} text files in {directory}")
        
        for filename in txt_files:
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Get file metadata
                file_stat = os.stat(filepath)
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                chunks = self.chunker.chunk(content)
                logger.info(f"Processed {filename}: {len(chunks)} chunks")
                
                for i, chunk in enumerate(chunks):
                    documents.append({
                        'text': chunk,
                        'source': filename,
                        'chunk_id': i,
                        'total_chunks': len(chunks),
                        'ingested_at': datetime.now().isoformat(),
                        'file_size': file_stat.st_size,
                        'content_hash': content_hash
                    })
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                continue
        
        logger.info(f"Total documents created: {len(documents)}")
        return documents
