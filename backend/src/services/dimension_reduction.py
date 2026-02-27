"""
Embedding dimension reduction for faster search
"""
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DimensionReducer:
    """Reduce embedding dimensions using PCA"""
    
    def __init__(self, target_dim: int = 128):
        """
        Initialize dimension reducer
        
        Args:
            target_dim: Target dimension (default 128, from 384)
        """
        self.target_dim = target_dim
        self.pca_matrix = None
        self.mean = None
        self.fitted = False
    
    def fit(self, embeddings: np.ndarray):
        """
        Fit PCA on embeddings
        
        Args:
            embeddings: (N, D) array of embeddings
        """
        if embeddings.shape[1] <= self.target_dim:
            logger.warning(f"Embeddings already {embeddings.shape[1]}D, no reduction needed")
            return
        
        # Center data
        self.mean = np.mean(embeddings, axis=0)
        centered = embeddings - self.mean
        
        # Compute covariance matrix
        cov = np.cov(centered.T)
        
        # Eigendecomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        
        # Sort by eigenvalue (descending)
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # Keep top k eigenvectors
        self.pca_matrix = eigenvectors[:, :self.target_dim]
        self.fitted = True
        
        # Calculate variance explained
        variance_explained = np.sum(eigenvalues[:self.target_dim]) / np.sum(eigenvalues)
        logger.info(f"PCA fitted: {embeddings.shape[1]}D → {self.target_dim}D "
                   f"(variance explained: {variance_explained:.2%})")
    
    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Reduce embedding dimensions
        
        Args:
            embeddings: (N, D) array of embeddings
            
        Returns:
            (N, target_dim) reduced embeddings
        """
        if not self.fitted:
            raise ValueError("Must call fit() before transform()")
        
        if embeddings.shape[1] <= self.target_dim:
            return embeddings
        
        # Center and project
        centered = embeddings - self.mean
        reduced = centered @ self.pca_matrix
        
        return reduced
    
    def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
        """Fit and transform in one step"""
        self.fit(embeddings)
        return self.transform(embeddings)


class EmbeddingConfig:
    """Configuration for embedding strategies"""
    
    def __init__(self, config: dict):
        self.model = config.get('model', 'all-MiniLM-L6-v2')
        self.dimension = config.get('dimension', 384)
        self.reduce_dimensions = config.get('reduce_dimensions', False)
        self.target_dimension = config.get('target_dimension', 128)
        
        self.reducer: Optional[DimensionReducer] = None
        if self.reduce_dimensions:
            self.reducer = DimensionReducer(self.target_dimension)
            logger.info(f"Dimension reduction enabled: {self.dimension}D → {self.target_dimension}D")
    
    def process_embeddings(self, embeddings: np.ndarray, fit: bool = False) -> np.ndarray:
        """
        Process embeddings with optional dimension reduction
        
        Args:
            embeddings: Raw embeddings
            fit: Whether to fit the reducer (only for training data)
            
        Returns:
            Processed embeddings
        """
        if not self.reduce_dimensions or self.reducer is None:
            return embeddings
        
        if fit:
            return self.reducer.fit_transform(embeddings)
        else:
            return self.reducer.transform(embeddings)
    
    def get_effective_dimension(self) -> int:
        """Get the effective embedding dimension after reduction"""
        if self.reduce_dimensions:
            return self.target_dimension
        return self.dimension
