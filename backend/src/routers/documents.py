"""
Document management endpoints router
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from models import DocumentCreate, DocumentUpdate
from dependencies import get_doc_manager, get_faiss_rag, get_metrics
from typing import Optional
import logging
import os

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


async def _add_to_collections_and_faiss(content: str, doc_id: str, metadata: dict, rag, domain: str = None):
    """Add document to xAI Collections first, then FAISS."""
    
    # Step 1: Try xAI Collections (if domain provided)
    xai_success = False
    if domain:
        try:
            from services.xai_collections import XAICollectionsClient
            xai_client = XAICollectionsClient(api_key=os.getenv("XAI_API_KEY"))
            
            # Get collection ID for domain
            collection_map = {
                "medical": os.getenv("MEDICAL_COLLECTION_ID"),
                "legal": os.getenv("LEGAL_COLLECTION_ID")
            }
            collection_id = collection_map.get(domain)
            
            if collection_id:
                await xai_client.add_documents(
                    collection_id=collection_id,
                    documents=[{
                        "text": content,
                        "metadata": {**metadata, "doc_id": doc_id}
                    }]
                )
                logger.info(f"✅ Added to xAI Collections ({domain}): {doc_id}")
                xai_success = True
        except Exception as e:
            logger.warning(f"xAI Collections add failed: {e}, will use FAISS only")
    
    # Step 2: Add to FAISS (always, as backup)
    if rag:
        try:
            chunks_added = rag.add_document_to_index(content, doc_id)
            logger.info(f"✅ Added to FAISS: {doc_id} ({chunks_added} chunks)")
            return {"xai_collections": xai_success, "faiss": True, "chunks": chunks_added}
        except Exception as e:
            logger.error(f"FAISS add failed: {e}")
            if not xai_success:
                raise  # Both failed
            return {"xai_collections": xai_success, "faiss": False, "chunks": 0}
    
    return {"xai_collections": xai_success, "faiss": False, "chunks": 0}


@router.post("")
async def create_document(
    request: Request, 
    doc: DocumentCreate,
    doc_manager=Depends(get_doc_manager),
    rag=Depends(get_faiss_rag),
    metrics=Depends(get_metrics)
):
    """Create document(s) - adds to xAI Collections then FAISS"""
    try:
        # Check if batch create
        body = await request.json()
        
        if 'documents' in body:
            # Batch create
            documents = body['documents']
            logger.info(f"Batch creating {len(documents)} documents")
            
            results = []
            for doc_data in documents:
                content = doc_data.get('content')
                metadata = doc_data.get('metadata', {})
                doc_id = doc_data.get('id')
                domain = doc_data.get('domain')  # Optional domain
                
                if not content:
                    continue
                
                result = doc_manager.add_document(content, metadata, doc_id)
                
                # Add to xAI Collections + FAISS
                index_result = await _add_to_collections_and_faiss(
                    result['content'], 
                    result['id'], 
                    metadata,
                    rag,
                    domain
                )
                result['indexed'] = index_result
                
                results.append(result)
                metrics['documents_created'] += 1
            
            logger.info(f"Batch created {len(results)} documents")
            return {"status": "created", "documents": results, "count": len(results)}
        
        else:
            # Single create
            logger.info(f"Creating document: {len(doc.content)} bytes")
            result = doc_manager.add_document(doc.content, doc.metadata, doc.id)
            
            # Add to xAI Collections + FAISS
            domain = doc.metadata.get('domain') if doc.metadata else None
            try:
                index_result = await _add_to_collections_and_faiss(
                    result['content'],
                    result['id'],
                    doc.metadata or {},
                    rag,
                    domain
                )
                result['indexed'] = index_result
            except Exception as e:
                logger.error(f"Failed to index, rolling back: {e}")
                doc_manager.delete_document(result['id'])
                raise HTTPException(status_code=500, detail=f"Failed to index document: {str(e)}")
            
            metrics['documents_created'] += 1
            logger.info(f"Document created: {result['id']}")
            return {"status": "created", "document": result}
            
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid document: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", dependencies=[Depends(get_doc_manager), Depends(get_metrics)])
async def list_documents(limit: int = 100, offset: int = 0):
    """List documents with pagination"""
    try:
        docs = doc_manager.list_documents(limit, offset)
        stats = doc_manager.get_stats()
        logger.info(f"Listed {len(docs)} documents")
        return {"documents": docs, "stats": stats, "count": len(docs)}
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_documents(q: str, limit: int = 10):
    """Search documents by content or metadata"""
    try:
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        results = doc_manager.search_documents(q, limit)
        logger.info(f"Search '{q}' returned {len(results)} results")
        return {"query": q, "results": results, "count": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """Get document by ID"""
    try:
        doc = doc_manager.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        logger.info(f"Retrieved document: {doc_id}")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{doc_id}")
async def update_document(request: Request, doc_id: str, doc: DocumentUpdate):
    """Update existing document"""
    try:
        logger.info(f"Updating document: {doc_id}")
        
        # Save original for rollback
        original = doc_manager.get_document(doc_id)
        if not original:
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_manager.update_document(doc_id, doc.content, doc.metadata)
        
        # Update in FAISS index
        if rag and doc.content:
            try:
                rag.update_document_in_index(doc_id, doc.content)
                logger.info(f"Updated {doc_id} in FAISS index")
            except Exception as e:
                logger.error(f"Failed to update in FAISS, rolling back: {e}")
                doc_manager.update_document(doc_id, original['content'], original['metadata'])
                raise HTTPException(status_code=500, detail=f"Failed to update index: {str(e)}")
        
        metrics['documents_updated'] += 1
        logger.info(f"Document updated: {doc_id} (version {result['version']})")
        return {"status": "updated", "document": result}
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid update: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}")
async def delete_document(request: Request, doc_id: str):
    """Delete document"""
    try:
        logger.info(f"Deleting document: {doc_id}")
        success = doc_manager.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Remove from FAISS index
        if rag:
            try:
                rag.remove_document_from_index(doc_id)
                logger.info(f"Removed {doc_id} from FAISS index")
            except Exception as e:
                logger.error(f"Failed to remove from FAISS: {e}")
        
        metrics['documents_deleted'] += 1
        logger.info(f"Document deleted: {doc_id}")
        return {"status": "deleted", "id": doc_id}
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid deletion: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
