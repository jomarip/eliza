from typing import Dict, List, Any
from .knowledge_graph import HatchyKnowledgeGraph
import logging

logger = logging.getLogger(__name__)

class EvolutionMapper:
    """Maps evolution chains and relationships between monsters."""
    
    def __init__(self, knowledge_graph: HatchyKnowledgeGraph):
        self.graph = knowledge_graph
        
    def get_chains(self, monsters: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Get evolution chains for the given monsters."""
        try:
            evolution_chains = {}
            
            for monster in monsters:
                monster_id = monster['id']
                chain = self._build_evolution_chain(monster_id)
                if chain:
                    base_form = chain[0]  # First monster in chain
                    evolution_chains[base_form] = chain[1:]  # Rest of chain
                    
            return evolution_chains
            
        except Exception as e:
            logger.error(f"Error getting evolution chains: {e}")
            return {}
            
    def _build_evolution_chain(self, monster_id: str) -> List[str]:
        """Build complete evolution chain for a monster."""
        chain = []
        current_id = monster_id
        
        # Build backwards (to base form)
        while True:
            monster = self.graph.get_entity(current_id)
            if not monster:
                break
                
            chain.insert(0, monster['name'])
            
            # Get previous form
            prev_rels = self.graph.get_relationships(
                current_id,
                relationship_type='evolves_from'
            )
            if not prev_rels:
                break
                
            current_id = prev_rels[0]['target']
            
        # Build forwards (evolved forms)
        current_id = monster_id
        while True:
            next_rels = self.graph.get_relationships(
                current_id,
                relationship_type='evolves_into'
            )
            if not next_rels:
                break
                
            current_id = next_rels[0]['target']
            monster = self.graph.get_entity(current_id)
            if not monster:
                break
                
            chain.append(monster['name'])
            
        return chain 