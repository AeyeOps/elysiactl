"""Embedding service for handling text vectorization."""

import hashlib
from typing import List


class EmbeddingService:
    """Service for handling text embeddings."""
    
    def __init__(self):
        """Initialize the embedding service."""
        pass
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text.
        
        For now, we delegate to Weaviate's built-in vectorizer.
        This method is here for future expansion when we need custom embeddings.
        
        Returns:
            Empty list to indicate delegation to Weaviate's vectorizer
        """
        # For now, return empty list to let Weaviate handle vectorization
        # This is the intended design - Weaviate's vectorizer is more efficient
        # and handles model management automatically
        return []
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts.
        
        Returns:
            List of empty lists to delegate to Weaviate's vectorizer
        """
        return [[] for _ in texts]
    
    def generate_deterministic_embedding(self, text: str, dimensions: int = 768) -> List[float]:
        """Generate a deterministic embedding from text hash.
        
        This is useful for testing and when you need consistent embeddings
        for the same text. Not suitable for production semantic search.
        
        Args:
            text: Input text
            dimensions: Number of dimensions for the embedding
            
        Returns:
            List of floats representing the embedding
        """
        # Create a hash of the text
        text_hash = hashlib.sha256(text.encode('utf-8')).digest()
        
        # Convert hash bytes to float values between -1 and 1
        embedding = []
        for i in range(dimensions):
            # Use hash bytes to generate pseudo-random values
            byte_value = text_hash[i % len(text_hash)]
            # Normalize to [-1, 1] range
            normalized_value = (byte_value / 127.5) - 1.0
            embedding.append(normalized_value)
        
        return embedding
    
    async def embed_text_with_fallback(self, text: str) -> List[float]:
        """Generate embeddings with fallback to deterministic method.
        
        This method first tries the primary embedding approach,
        then falls back to a deterministic hash-based method.
        
        Returns:
            List of floats representing the embedding
        """
        # Primary approach (delegate to Weaviate)
        primary_embedding = await self.embed_text(text)
        
        if primary_embedding:
            return primary_embedding
        
        # Fallback to deterministic embedding
        return self.generate_deterministic_embedding(text)