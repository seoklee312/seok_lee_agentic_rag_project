"""
Document Management Service
Handles CRUD operations for documents with versioning and metadata tracking
"""
import json
import logging
import hashlib
import threading
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages document lifecycle with persistence"""
    
    def __init__(self, storage_path: str = "../faiss_index/documents.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.documents = self._load_documents()
        logger.info(f"DocumentManager initialized with {len(self.documents)} documents")
    
    def _load_documents(self) -> Dict[str, Dict]:
        """Load documents from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    docs = json.load(f)
                    logger.info(f"Loaded {len(docs)} documents from {self.storage_path}")
                    return docs
        except Exception as e:
            logger.error(f"Failed to load documents: {e}")
        return {}
    
    def _save_documents(self):
        """Persist documents to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.documents, f, indent=2)
            logger.info(f"Saved {len(self.documents)} documents to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save documents: {e}")
            raise
    
    def add_document(self, content: str, metadata: Optional[Dict] = None, custom_id: Optional[str] = None) -> Dict:
        """Add new document with metadata"""
        with self._lock:
            try:
                # Check document limit
                if len(self.documents) >= 10000:
                    raise ValueError("Document limit reached (10,000 max)")
                
                doc_id = custom_id if custom_id else str(uuid.uuid4())
                
                # Check if custom ID already exists
                if custom_id and doc_id in self.documents:
                    raise ValueError(f"Document with ID {doc_id} already exists")
                
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                
                # Check for duplicate content
                for existing_doc in self.documents.values():
                    if existing_doc['content_hash'] == content_hash:
                        logger.warning(f"Duplicate content detected (hash: {content_hash[:8]})")
                        raise ValueError(f"Duplicate document content (existing ID: {existing_doc['id']})")
                
                doc = {
                    "id": doc_id,
                    "content": content,
                    "content_hash": content_hash,
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "version": 1,
                    "size_bytes": len(content)
                }
                
                self.documents[doc_id] = doc
                self._save_documents()
                
                logger.info(f"Added document {doc_id} ({len(content)} bytes, hash: {content_hash[:8]})")
                return doc
            except ValueError:
                raise
            except Exception as e:
                logger.error(f"Failed to add document: {e}")
                raise ValueError(f"Failed to add document: {str(e)}")
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Retrieve document by ID"""
        with self._lock:
            try:
                doc = self.documents.get(doc_id)
                if doc:
                    logger.debug(f"Retrieved document {doc_id}")
                else:
                    logger.warning(f"Document {doc_id} not found")
                return doc
            except Exception as e:
                logger.error(f"Failed to get document {doc_id}: {e}")
                return None
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List documents with pagination"""
        with self._lock:
            try:
                docs = list(self.documents.values())
                docs.sort(key=lambda x: x['created_at'], reverse=True)
                paginated = docs[offset:offset + limit]
                logger.info(f"Listed {len(paginated)} documents (offset={offset}, limit={limit})")
                return paginated
            except Exception as e:
                logger.error(f"Failed to list documents: {e}")
                return []
    
    def update_document(self, doc_id: str, content: str, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Update existing document with versioning"""
        with self._lock:
            try:
                if doc_id not in self.documents:
                    logger.warning(f"Cannot update non-existent document {doc_id}")
                    return None
                
                doc = self.documents[doc_id]
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                
                doc["content"] = content
                doc["content_hash"] = content_hash
                doc["updated_at"] = datetime.utcnow().isoformat()
                doc["version"] += 1
                
                if metadata:
                    doc["metadata"].update(metadata)
                
                self._save_documents()
                logger.info(f"Updated document {doc_id} to version {doc['version']}")
                return doc
            except Exception as e:
                logger.error(f"Failed to update document {doc_id}: {e}")
                raise ValueError(f"Failed to update document: {str(e)}")
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID"""
        with self._lock:
            try:
                if doc_id in self.documents:
                    del self.documents[doc_id]
                    self._save_documents()
                    logger.info(f"Deleted document {doc_id}")
                    return True
                logger.warning(f"Cannot delete non-existent document {doc_id}")
                return False
            except Exception as e:
                logger.error(f"Failed to delete document {doc_id}: {e}")
                raise ValueError(f"Failed to delete document: {str(e)}")
    
    def get_stats(self) -> Dict:
        """Get document statistics"""
        with self._lock:
            try:
                total = len(self.documents)
                total_size = sum(len(d['content']) for d in self.documents.values())
                
                stats = {
                    "total_documents": total,
                    "total_size_bytes": total_size,
                    "avg_size_bytes": total_size // total if total > 0 else 0,
                    "limit": 10000,
                    "remaining": 10000 - total
                }
                logger.debug(f"Document stats: {stats}")
                return stats
            except Exception as e:
                logger.error(f"Failed to get stats: {e}")
                return {"total_documents": 0, "total_size_bytes": 0, "avg_size_bytes": 0, "limit": 10000, "remaining": 10000}
    
    def search_documents(self, query: str, limit: int = 10) -> List[Dict]:
        """Search documents by content or metadata"""
        with self._lock:
            try:
                query_lower = query.lower()
                results = []
                
                for doc in self.documents.values():
                    # Search in content
                    if query_lower in doc['content'].lower():
                        results.append(doc)
                        continue
                    
                    # Search in metadata
                    metadata_str = json.dumps(doc['metadata']).lower()
                    if query_lower in metadata_str:
                        results.append(doc)
                
                # Sort by relevance (number of occurrences)
                results.sort(
                    key=lambda d: d['content'].lower().count(query_lower),
                    reverse=True
                )
                
                limited_results = results[:limit]
                logger.info(f"Search '{query}' found {len(results)} documents, returning {len(limited_results)}")
                return limited_results
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return []
