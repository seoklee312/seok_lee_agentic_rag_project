"""
xAI Collections API Client for RAG vector store
"""
import logging
from typing import List, Dict, Any, Optional
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class XAICollectionsClient:
    """xAI Collections API client for document storage and retrieval"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url', 'https://api.x.ai/v1')
        self.default_collection = config.get('default_collection', 'rag_demo')
        self.top_k = config.get('top_k', 10)
        self.timeout = config.get('timeout', 30)
        
        # Cache collection IDs
        self._collection_cache = {}
        
        logger.info(f"XAICollectionsClient initialized with collection={self.default_collection}")
    
    async def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new collection
        
        Args:
            name: Collection name
            description: Optional description
            metadata: Optional metadata dict
        
        Returns:
            Collection ID
        """
        url = f"{self.base_url}/collections"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # xAI Collections requires field_definitions
        payload = {
            "collection_name": name,
            "field_definitions": [
                {
                    "key": "content",
                    "name": "Content",
                    "type": "text",
                    "required": True,
                    "inject_into_chunk": True,
                    "unique": False
                }
            ]
        }
        
        if description:
            payload["collection_description"] = description
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to create collection: {error_text}")
                
                data = await response.json()
                collection_id = data.get('collection_id')
                
                # Cache collection ID
                self._collection_cache[name] = collection_id
                
                logger.info(f"Created collection '{name}' with ID: {collection_id}")
                return collection_id
    
    async def get_collection(self, name: str) -> Optional[str]:
        """
        Get collection ID by name
        
        Args:
            name: Collection name
        
        Returns:
            Collection ID or None if not found
        """
        # Check cache first
        if name in self._collection_cache:
            return self._collection_cache[name]
        
        url = f"{self.base_url}/collections"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                collections = data.get('collections', [])
                
                for collection in collections:
                    coll_name = collection.get('collection_name') or collection.get('name')
                    if coll_name == name:
                        collection_id = collection.get('collection_id') or collection.get('id')
                        self._collection_cache[name] = collection_id
                        return collection_id
                
                return None
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add documents to collection via Files API
        
        Args:
            documents: List of document dicts with 'content', 'metadata', etc.
            collection_name: Collection name (default: default_collection)
        
        Returns:
            Response with file IDs
        """
        collection_name = collection_name or self.default_collection
        
        # Get or create collection
        collection_id = await self.get_collection(collection_name)
        if not collection_id:
            collection_id = await self.create_collection(collection_name)
        
        # Upload files with collection_id parameter
        file_ids = []
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            
            # Create temporary file
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                # Upload file with collection_id
                url = f"{self.base_url}/files"
                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    with open(temp_path, 'rb') as file_data:
                        form = aiohttp.FormData()
                        form.add_field('file', file_data, filename=f'doc_{i}.txt', content_type='text/plain')
                        form.add_field('collection_id', collection_id)  # Add to collection during upload
                        
                        async with session.post(url, data=form, headers=headers) as response:
                            if response.status not in [200, 201]:
                                error_text = await response.text()
                                logger.warning(f"Failed to upload file: {error_text}")
                                continue
                            
                            data = await response.json()
                            file_id = data.get('id')
                            if file_id:
                                file_ids.append(file_id)
            finally:
                # Clean up temp file
                os.unlink(temp_path)
        
        if not file_ids:
            raise Exception("No files uploaded successfully")
        
        logger.info(f"Added {len(file_ids)} files to collection '{collection_name}'")
        return {"success": True, "file_ids": file_ids, "count": len(file_ids)}
    
    async def query(
        self,
        query_text: str,
        collection_name: Optional[str] = None,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query collection for relevant documents using /documents/search
        
        Args:
            query_text: Query string
            collection_name: Collection name (default: default_collection)
            top_k: Number of results (default: config top_k)
            filters: Optional metadata filters (AIP-160 syntax)
        
        Returns:
            List of matching documents with scores
        """
        collection_name = collection_name or self.default_collection
        top_k = top_k or self.top_k
        
        # Get collection ID
        collection_id = await self.get_collection(collection_name)
        if not collection_id:
            logger.warning(f"Collection '{collection_name}' not found")
            return []
        
        url = f"{self.base_url}/documents/search"  # Correct endpoint
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query_text,
            "source": {
                "collection_ids": [collection_id]
            },
            "retrieval_mode": {"type": "hybrid"},  # Use hybrid search
            "top_k": top_k
        }
        
        if filters:
            payload["filter"] = filters
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to query collection: {error_text}")
                
                data = await response.json()
                results = data.get('results', [])
                
                logger.info(f"Query returned {len(results)} results from '{collection_name}'")
                return results
    
    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection
        
        Args:
            collection_name: Collection name
        
        Returns:
            True if deleted successfully
        """
        collection_id = await self.get_collection(collection_name)
        if not collection_id:
            logger.warning(f"Collection '{collection_name}' not found")
            return False
        
        url = f"{self.base_url}/collections/{collection_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to delete collection: {error_text}")
                
                # Remove from cache
                if collection_name in self._collection_cache:
                    del self._collection_cache[collection_name]
                
                logger.info(f"Deleted collection '{collection_name}'")
                return True
