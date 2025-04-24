"""
Memory Manager for Clara AI

This module handles memory storage and retrieval operations for the Clara AI agent system.
It provides a unified interface for storing, retrieving, and managing contextual information.
"""

from langgraph.store.memory import InMemoryStore
from typing import Any, Dict, List, Optional
import logging

class MemoryManager:
    """
    Manages memory storage and retrieval for the agent system.
    
    This class provides an abstraction layer over the underlying memory store,
    handling operations like storing, retrieving, and searching memory.
    """
    
    def __init__(self, embedding_model: str = "azure_openai:text-embedding-ada-002-2"):
        """
        Initialize the memory manager with a specific embedding model.
        
        Args:
            embedding_model: The model to use for text embeddings in memory indexing
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.store = InMemoryStore(
            index={"embed": embedding_model}
        )
        self.logger.debug(f"Initialized MemoryManager with embedding model: {embedding_model}")
    
    def get_store(self):
        """
        Get the underlying memory store.
        
        Returns:
            The memory store instance
        """
        return self.store
    
    def add_memory(self, key: str, content: Any) -> None:
        """
        Add an item to memory.
        
        Args:
            key: The key to store the memory under
            content: The content to store in memory
        """
        self.store.memory_write(key, content)
        self.logger.debug(f"Added memory with key: {key}")
    
    def get_memory(self, key: str) -> Optional[Any]:
        """
        Retrieve an item from memory by key.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The memory content or None if not found
        """
        try:
            result = self.store.memory_read(key)
            return result
        except KeyError:
            self.logger.debug(f"Memory key not found: {key}")
            return None
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memory using semantic similarity.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory items with their scores
        """
        results = self.store.memory_search(query, limit=limit)
        self.logger.debug(f"Memory search for '{query}' returned {len(results)} results")
        return results