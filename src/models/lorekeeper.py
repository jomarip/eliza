from typing import Dict, Any, Optional, List
from .enhanced_chatbot import EnhancedChatbot
from .knowledge_graph import HatchyKnowledgeGraph
from cachetools import LRUCache
import logging

logger = logging.getLogger(__name__)

class LorekeeperAgent(EnhancedChatbot):
    """Lorekeeper agent for managing Hatchyverse knowledge."""
    
    def __init__(self, knowledge_graph: HatchyKnowledgeGraph, llm_client=None):
        super().__init__(llm_client)
        self.graph = knowledge_graph
        self.cache = LRUCache(1000)  # Cache recent queries
        
    def generate_response(self, query: str, history: Optional[list] = None) -> Dict[str, Any]:
        """Generate a response to a query using the knowledge graph."""
        # Check cache first
        cache_key = f"{query}_{str(history)}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        # Query knowledge graph
        context = self.graph.query(query, depth=2)
        
        # Generate with context
        response = super().generate_response(query, context, history)
        
        # Update cache
        self.cache.put(cache_key, response)
        return response
        
    def validate_submission(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a lore submission against existing knowledge."""
        return self.graph.validate_lore(
            submission, 
            rules=self.config['validation_rules']
        ) 