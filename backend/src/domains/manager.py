"""
Domain Manager - Dynamic domain loading and switching
"""
import os
import yaml
import logging
from typing import Dict, Optional, List
from pathlib import Path
from .base import BaseDomain
from .medical import MedicalDomain
from .legal import LegalDomain
from utils.errors import DomainError, ConfigError

logger = logging.getLogger(__name__)


class DomainManager:
    """Manages domain loading and switching"""
    
    # Registry of available domains
    DOMAIN_REGISTRY = {
        'medical': MedicalDomain,
        'legal': LegalDomain
    }
    
    def __init__(self, domains_path: Optional[str] = None, collections_client=None):
        """
        Initialize domain manager
        
        Args:
            domains_path: Path to domains directory (default: auto-detect)
            collections_client: xAI Collections client for data source loading
        """
        if domains_path is None:
            # Auto-detect domains path
            domains_path = Path(__file__).parent
        
        self.domains_path = Path(domains_path)
        self.active_domain: Optional[BaseDomain] = None
        self.loaded_domains: Dict[str, BaseDomain] = {}
        self.collections_client = collections_client
        
        logger.info(f"DomainManager initialized with path: {self.domains_path}")
    
    def load_domain(self, domain_name: str) -> BaseDomain:
        """
        Load a domain by name
        
        Args:
            domain_name: Name of domain to load (medical, legal, etc.)
        
        Returns:
            Loaded domain instance
        """
        # Check if already loaded
        if domain_name in self.loaded_domains:
            logger.info(f"Domain '{domain_name}' already loaded")
            return self.loaded_domains[domain_name]
        
        # Check if domain exists in registry
        if domain_name not in self.DOMAIN_REGISTRY:
            raise DomainError(
                f"Unknown domain: {domain_name}",
                domain=domain_name,
                available=list(self.DOMAIN_REGISTRY.keys())
            )
        
        # Load domain config
        config_path = self.domains_path / domain_name / 'config.yaml'
        if not config_path.exists():
            raise ConfigError(
                f"Domain config not found",
                config_path=str(config_path),
                domain=domain_name
            )
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise ConfigError(
                f"Failed to load domain config: {e}",
                config_path=str(config_path),
                domain=domain_name
            )
        
        # Instantiate domain
        domain_class = self.DOMAIN_REGISTRY[domain_name]
        domain = domain_class(config)
        
        # Cache loaded domain
        self.loaded_domains[domain_name] = domain
        
        logger.info(f"Loaded domain: {domain_name}")
        return domain
    
    async def load_domain_data(self, domain_name: str) -> Optional[str]:
        """
        Load domain data sources into Collections
        
        Args:
            domain_name: Domain to load data for
        
        Returns:
            Collection ID if created, None otherwise
        """
        if not self.collections_client:
            logger.warning("No Collections client - skipping data load")
            return None
        
        domain = self.load_domain(domain_name)
        config = self.get_domain_config(domain_name)
        
        # Check if collection already exists
        collection_id = config.get('collection_id')
        if collection_id:
            logger.info(f"Domain '{domain_name}' already has collection: {collection_id}")
            return collection_id
        
        # Get sample documents
        sample_docs = config.get('sample_documents', [])
        if not sample_docs:
            logger.info(f"No sample documents for domain '{domain_name}'")
            return None
        
        try:
            # Create collection
            collection_name = f"{domain_name}_knowledge_base"
            collection_id = await self.collections_client.create_collection(
                name=collection_name,
                description=config.get('description', f'{domain_name} domain knowledge base')
            )
            
            # Upload documents
            await self.collections_client.add_documents(sample_docs, collection_name)
            
            # Update config with collection ID
            config['collection_id'] = collection_id
            config_path = self.domains_path / domain_name / 'config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            logger.info(f"Loaded {len(sample_docs)} documents for domain '{domain_name}' into collection {collection_id}")
            return collection_id
            
        except Exception as e:
            logger.error(f"Failed to load domain data: {e}")
            raise DomainError(
                f"Failed to load data sources for domain",
                domain=domain_name,
                error=str(e)
            )
    
    def switch_domain(self, domain_name: str) -> BaseDomain:
        """
        Switch to a different domain
        
        Args:
            domain_name: Name of domain to switch to
        
        Returns:
            Activated domain instance
        """
        domain = self.load_domain(domain_name)
        self.active_domain = domain
        logger.info(f"Switched to domain: {domain_name}")
        return domain
    
    def get_active_domain(self) -> Optional[BaseDomain]:
        """Get currently active domain"""
        return self.active_domain
    
    def list_available_domains(self) -> List[str]:
        """List all available domains"""
        return list(self.DOMAIN_REGISTRY.keys())
    
    def get_domain_config(self, domain_name: str) -> Dict:
        """Get configuration for a specific domain"""
        config_path = self.domains_path / domain_name / 'config.yaml'
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ConfigError(
                f"Failed to read domain config",
                config_path=str(config_path),
                domain=domain_name,
                error=str(e)
            )
