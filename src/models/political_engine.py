from typing import Dict, List, Any
from .knowledge_graph import HatchyKnowledgeGraph
import logging

logger = logging.getLogger(__name__)

class PoliticalEngine:
    """Analyzes political relationships and conflicts."""
    
    def __init__(self, knowledge_graph: HatchyKnowledgeGraph):
        self.graph = knowledge_graph
        
    def detect_conflicts(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect political conflicts based on filters."""
        try:
            # Get relevant factions
            factions = self.graph.get_entities_by_type('faction')
            if not factions:
                return []
                
            conflicts = []
            for faction in factions:
                # Get faction relationships
                relationships = self.graph.get_relationships(
                    faction['id'],
                    relationship_type='opposes'
                )
                
                for rel in relationships:
                    conflict = {
                        'parties': [
                            self.graph.get_entity_name(rel['source']),
                            self.graph.get_entity_name(rel['target'])
                        ],
                        'type': rel.get('attributes', {}).get('conflict_type', 'unknown'),
                        'status': rel.get('attributes', {}).get('status', 'active'),
                        'region': rel.get('attributes', {}).get('region', 'unknown')
                    }
                    
                    # Apply filters
                    if self._matches_filters(conflict, filters):
                        conflicts.append(conflict)
                        
            return conflicts
            
        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return []
            
    def _matches_filters(self, conflict: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if conflict matches the given filters."""
        for key, value in filters.items():
            if key in conflict:
                if isinstance(value, list):
                    if conflict[key] not in value:
                        return False
                elif conflict[key] != value:
                    return False
        return True 