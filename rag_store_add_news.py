#!/usr/bin/env python3
"""
Add domain-specific news to RAG stores (xAI Collections + FAISS)
Fetches real news for configured domains: medical, legal
"""
import sys
import os
import asyncio
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import html
import re

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from services.xai_collections import XAICollectionsClient
from services.faiss import DocumentManager
import yaml

# Domain-specific RSS feeds
DOMAIN_FEEDS = {
    'medical': [
        'https://www.sciencedaily.com/rss/health_medicine.xml',
        'https://www.medicalnewstoday.com/rss/news.xml',
    ],
    'legal': [
        'https://www.law.com/rss/',
        'https://www.scotusblog.com/feed/',
    ]
}

ARTICLES_PER_DOMAIN = 30

def clean_text(text):
    """Clean HTML and normalize whitespace"""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub('<[^<]+?>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fetch_rss_articles(url, limit=15):
    """Fetch articles from RSS feed"""
    articles = []
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        
        # Try different RSS formats
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
        
        for item in items[:limit]:
            # Extract title
            title_elem = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
            title = clean_text(title_elem.text if title_elem is not None else '')
            
            # Extract description/content
            desc_elem = (item.find('description') or 
                        item.find('summary') or 
                        item.find('{http://www.w3.org/2005/Atom}summary') or
                        item.find('content'))
            description = clean_text(desc_elem.text if desc_elem is not None else '')
            
            # Extract publication date
            pub_date_elem = (item.find('pubDate') or 
                           item.find('published') or 
                           item.find('{http://www.w3.org/2005/Atom}published'))
            pub_date = clean_text(pub_date_elem.text if pub_date_elem is not None else '')
            
            if title and description:
                # Limit content length
                sentences = description.split('. ')
                content = '. '.join(sentences[:5]) + '.'
                
                articles.append({
                    'title': title[:200],
                    'content': content[:1000],
                    'pub_date': pub_date or datetime.now().isoformat()
                })
                
                if len(articles) >= limit:
                    break
    except Exception as e:
        print(f"  ⚠️  Error fetching from {url[:50]}...: {e}")
    
    return articles

def fetch_domain_news(domain, limit=30):
    """Fetch news for a specific domain"""
    print(f"\n📡 Fetching {domain} news...")
    feeds = DOMAIN_FEEDS.get(domain, [])
    
    all_articles = []
    per_feed = (limit // len(feeds)) + 1 if feeds else 0
    
    for feed_url in feeds:
        articles = fetch_rss_articles(feed_url, per_feed)
        all_articles.extend(articles)
        print(f"  ✓ {len(articles)} articles from {feed_url[:40]}...")
    
    # Limit to requested amount
    all_articles = all_articles[:limit]
    print(f"  ✅ Total: {len(all_articles)} {domain} articles")
    
    return all_articles

def create_evidence(article, domain, ingestion_timestamp):
    """Create evidence document with metadata"""
    # Generate unique ID
    title_slug = re.sub(r'[^a-z0-9]+', '_', article['title'].lower())[:50]
    doc_id = f"{ingestion_timestamp}_{domain}_{title_slug}"
    
    # Format content with domain context
    content = f"[{domain.upper()}] {article['title']}\n\n{article['content']}"
    
    return {
        'id': doc_id,
        'title': article['title'],
        'content': content,
        'metadata': {
            'domain': domain,
            'title': article['title'],
            'news_date': article['pub_date'],
            'ingestion_date': ingestion_timestamp,
            'source': 'rss_feed',
            'category': domain
        }
    }

async def add_to_xai_collections(evidences, config):
    """Add documents to xAI Collections"""
    xai_config = config.get('xai_collections', {})
    if not xai_config.get('enabled', False):
        print("⚠️  xAI Collections not enabled")
        return 0
    
    try:
        client = XAICollectionsClient(xai_config)
        collection_name = xai_config.get('default_collection', 'rag_demo')
        
        print(f"\n📦 Adding to xAI Collections: {collection_name}")
        
        # Create collection if not exists
        try:
            await client.create_collection(
                name=collection_name,
                description="Domain-specific news collection"
            )
            print(f"  ✓ Collection ready: {collection_name}")
        except:
            pass
        
        # Add documents
        added = 0
        for i, evidence in enumerate(evidences, 1):
            try:
                await client.add_documents([evidence], collection_name)
                domain_tag = "⚕️" if evidence['metadata']['domain'] == 'medical' else "⚖️"
                print(f"  [{i}/{len(evidences)}] {domain_tag} {evidence['title'][:60]}...")
                added += 1
            except Exception as e:
                print(f"  ⚠️  Failed [{i}]: {str(e)[:50]}")
        
        print(f"✅ Added {added}/{len(evidences)} to xAI Collections")
        return added
    except Exception as e:
        print(f"❌ xAI Collections error: {e}")
        return 0

def add_to_faiss(evidences):
    """Add documents to FAISS index"""
    print(f"\n📦 Adding to FAISS index...")
    
    try:
        doc_manager = DocumentManager()
        
        added = 0
        for i, evidence in enumerate(evidences, 1):
            try:
                doc_manager.add_document(
                    content=evidence['content'],
                    metadata=evidence['metadata'],
                    custom_id=evidence['id']
                )
                domain_tag = "⚕️" if evidence['metadata']['domain'] == 'medical' else "⚖️"
                print(f"  [{i}/{len(evidences)}] {domain_tag} {evidence['title'][:60]}...")
                added += 1
            except Exception as e:
                print(f"  ⚠️  Failed [{i}]: {str(e)[:50]}")
        
        print(f"✅ Added {added}/{len(evidences)} to FAISS")
        return added
    except Exception as e:
        print(f"❌ FAISS error: {e}")
        return 0

async def main():
    """Main execution"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        📰 ADD DOMAIN NEWS TO RAG STORES                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # Load config
    config_path = "backend/config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    ingestion_timestamp = datetime.now().isoformat()
    
    # Fetch news for each domain
    all_evidences = []
    domain_counts = {}
    
    for domain in ['medical', 'legal']:
        articles = fetch_domain_news(domain, ARTICLES_PER_DOMAIN)
        domain_counts[domain] = len(articles)
        
        for article in articles:
            evidence = create_evidence(article, domain, ingestion_timestamp)
            all_evidences.append(evidence)
    
    print("\n" + "="*60)
    print(f"\n📊 Fetched {len(all_evidences)} total articles:")
    print(f"  ⚕️  Medical: {domain_counts.get('medical', 0)} articles")
    print(f"  ⚖️  Legal:   {domain_counts.get('legal', 0)} articles")
    
    if not all_evidences:
        print("\n❌ No articles fetched. Check RSS feeds.")
        return
    
    # Add to RAG stores
    print("\n" + "="*60)
    print("\n1️⃣  xAI Collections (Primary)")
    print("-" * 60)
    xai_count = await add_to_xai_collections(all_evidences, config)
    
    print("\n2️⃣  FAISS Index (Fallback)")
    print("-" * 60)
    faiss_count = add_to_faiss(all_evidences)
    
    # Summary
    print("\n" + "="*60)
    print("\n📊 FINAL SUMMARY")
    print("-" * 60)
    print(f"  Articles fetched:    {len(all_evidences)}")
    print(f"    ⚕️  Medical:        {domain_counts.get('medical', 0)}")
    print(f"    ⚖️  Legal:          {domain_counts.get('legal', 0)}")
    print(f"  xAI Collections:     {xai_count} added")
    print(f"  FAISS Index:         {faiss_count} added")
    print(f"  Ingestion date:      {ingestion_timestamp}")
    print("\n✅ Domain news added to RAG stores")
    print("\n💡 TIP: Query with domain context:")
    print("   curl -X POST http://localhost:8000/v1/query \\")
    print("     -d '{\"question\": \"What are the latest medical breakthroughs?\"}'")

if __name__ == "__main__":
    asyncio.run(main())
