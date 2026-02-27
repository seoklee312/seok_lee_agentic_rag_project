#!/usr/bin/env python3
"""
Wipe out all documents from RAG stores (xAI Collections + FAISS)
"""
import sys
import os
import asyncio

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from services.xai_collections import XAICollectionsClient
from services.faiss import FaissRAGEngine, DocumentManager
import yaml

async def wipe_xai_collections(config):
    """Delete all documents from xAI Collections"""
    xai_config = config.get('xai_collections', {})
    if not xai_config.get('enabled', False):
        print("⚠️  xAI Collections not enabled")
        return 0
    
    try:
        client = XAICollectionsClient(xai_config)
        collection_name = xai_config.get('default_collection', 'rag_demo')
        
        print(f"🔍 Checking xAI Collections: {collection_name}")
        
        # Try to delete collection
        try:
            await client.delete_collection(collection_name)
            print(f"✅ Deleted xAI collection: {collection_name}")
            return 1
        except Exception as e:
            print(f"⚠️  Collection not found or already deleted: {e}")
            return 0
    except Exception as e:
        print(f"❌ xAI Collections error: {e}")
        return 0

def wipe_faiss_index():
    """Delete all documents from FAISS index"""
    print("\n🔍 Checking FAISS index...")
    
    try:
        config_path = "backend/config.yaml"
        doc_manager = DocumentManager()
        
        # Get all document IDs
        all_docs = doc_manager.list_documents()
        total = len(all_docs)
        
        if total == 0:
            print("✅ FAISS index is already empty")
            return 0
        
        print(f"📊 Found {total} documents in FAISS")
        
        # Delete all
        print("🔄 Deleting documents...")
        for i, doc in enumerate(all_docs, 1):
            doc_id = doc.get('id')
            if doc_id:
                doc_manager.delete_document(doc_id)
                print(f"  [{i}/{total}] Deleted: {doc_id}")
        
        print(f"✅ Wiped {total} documents from FAISS index")
        return total
    except Exception as e:
        print(f"❌ FAISS error: {e}")
        return 0

async def main():
    """Wipe all RAG stores"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           🗑️  RAG STORE RESET                                ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    
    # Load config
    config_path = "backend/config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Confirm
    response = input("⚠️  Delete all documents from xAI Collections + FAISS? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    print("\n" + "="*60)
    
    # 1. Wipe xAI Collections (primary)
    print("\n1️⃣  xAI Collections (Primary)")
    print("-" * 60)
    xai_count = await wipe_xai_collections(config)
    
    # 2. Wipe FAISS (fallback)
    print("\n2️⃣  FAISS Index (Fallback)")
    print("-" * 60)
    faiss_count = wipe_faiss_index()
    
    # Summary
    print("\n" + "="*60)
    print("\n📊 SUMMARY")
    print("-" * 60)
    print(f"  xAI Collections: {xai_count} collection(s) deleted")
    print(f"  FAISS Index:     {faiss_count} document(s) deleted")
    print(f"  Total:           {xai_count + faiss_count} items removed")
    print("\n✅ RAG stores reset complete")

if __name__ == "__main__":
    asyncio.run(main())
