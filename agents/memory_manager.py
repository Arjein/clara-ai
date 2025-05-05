"""
Memory Manager for Clara AI

This module handles memory storage and retrieval operations for the Clara AI agent system.
It provides a unified interface for storing, retrieving, and managing contextual information.
"""

from langgraph.store.memory import InMemoryStore
from typing import Any, Dict, List, Optional, Literal
import logging
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_ollama.embeddings import OllamaEmbeddings
class MemoryManager:
    """
    Manages memory storage and retrieval for the agent system.
    
    This class provides an abstraction layer over the underlying memory store,
    handling operations like storing, retrieving, and searching memory.
    """
    
    def __init__(self, embedding_model: str = "local:all-minilm", 
                 model_type: Literal["azure", "ollama", "huggingface", "local"] = "local"):
        """ 
        Initialize the memory manager with a specific embedding model.
        
        Args:
            embedding_model: The model to use for text embeddings in memory indexing
            model_type: The type of model provider to use
                - "azure": Use Azure OpenAI (paid)
                - "ollama": Use local Ollama models (free)
                - "huggingface": Use Hugging Face models (free)
                - "local": Use local embedding models (free)
        """
        self.logger = logging.getLogger("ClaraSecretary")
        
        # Setup embedding model based on type
        embeddings = None
        
        if model_type == "azure":
            # Original Azure OpenAI option (paid)
            embedding_spec = embedding_model
        elif model_type == "ollama":
            # Ollama embeddings - free, uses local Ollama server
            embeddings = OllamaEmbeddings(model=embedding_model)
            embedding_spec = {"embed": embeddings}
        elif model_type == "huggingface" or model_type == "local":
            # Hugging Face embeddings - free, runs locally
            if model_type == "local" and embedding_model == "local:all-minilm":
                # Default to a good small embedding model
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
            else:
                # Use specified model
                model_name = embedding_model.replace("local:", "")
                if ":" not in embedding_model and not embedding_model.startswith("sentence-transformers/"):
                    model_name = f"sentence-transformers/{model_name}"
            
            embeddings = HuggingFaceEmbeddings(model_name=model_name)
            embedding_spec = {"embed": embeddings}
        
        self.store = InMemoryStore(index=embedding_spec)
        self.logger.debug(f"Initialized MemoryManager with embedding model: {embedding_model} (type: {model_type})")
    
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