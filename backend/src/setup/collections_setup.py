"""Setup xAI Collections for demo - One-time initialization."""
import asyncio
import os
import sys
import logging

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.xai_collections import XAICollectionsClient
from domains.manager import DomainManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_collections():
    """
    One-time setup: Create xAI Collections and populate with domain documents.
    """
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        logger.error("❌ XAI_API_KEY not found in environment")
        return
    
    logger.info("🚀 Starting xAI Collections setup...")
    
    client = XAICollectionsClient(api_key=api_key)
    domain_manager = DomainManager()
    
    collection_ids = {}
    
    for domain_name in ["medical", "legal"]:
        logger.info(f"\n📦 Setting up {domain_name} collection...")
        
        try:
            # Get domain config
            domain = domain_manager.get_domain(domain_name)
            config = domain.config
            
            # Create collection
            collection_name = f"{domain_name}_knowledge"
            logger.info(f"Creating collection: {collection_name}")
            
            collection = await client.create_collection(
                name=collection_name,
                embedding_model="xai-embed-large"
            )
            
            logger.info(f"✅ Collection created: {collection.id}")
            
            # Upload documents from config
            documents = config.get('sample_documents', [])
            if documents:
                # Format for xAI Collections API
                formatted_docs = [
                    {
                        "text": doc.get('content', ''),
                        "metadata": doc.get('metadata', {})
                    }
                    for doc in documents
                ]
                
                await client.add_documents(
                    collection_id=collection.id,
                    documents=formatted_docs
                )
                logger.info(f"✅ Uploaded {len(documents)} documents")
            
            collection_ids[domain_name] = collection.id
        
        except Exception as e:
            logger.error(f"❌ Failed to setup {domain_name}: {e}")
            continue
    
    # Save to .env
    if collection_ids:
        logger.info("\n💾 Saving collection IDs to .env...")
        
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
        
        with open(env_path, 'a') as f:
            f.write(f"\n# xAI Collections (auto-generated)\n")
            for domain, cid in collection_ids.items():
                f.write(f"{domain.upper()}_COLLECTION_ID={cid}\n")
        
        logger.info("✅ Collection IDs saved to .env")
    
    logger.info("\n🎉 Setup complete!")
    logger.info(f"Collections created: {list(collection_ids.keys())}")
    
    return collection_ids


if __name__ == "__main__":
    try:
        result = asyncio.run(setup_collections())
        if result:
            print("\n✅ SUCCESS! Collections ready for use.")
            print("Restart your application to use xAI Collections.")
        else:
            print("\n❌ FAILED! Check logs above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
