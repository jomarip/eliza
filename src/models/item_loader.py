from pathlib import Path
import pandas as pd
from .knowledge_graph import HatchyKnowledgeGraph
import logging

logger = logging.getLogger(__name__)

class ItemLoader:
    """Loads item and equipment data into the knowledge graph."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
    def load(self, graph: HatchyKnowledgeGraph) -> None:
        """Load item data into the knowledge graph."""
        try:
            # Load equipment data if exists
            equipment_path = self.data_dir / "equipment.csv"
            if equipment_path.exists():
                self._process_equipment(equipment_path, graph)
                
        except Exception as e:
            logger.error(f"Error loading item data: {str(e)}")
            raise
            
    def _process_equipment(self, file_path: Path, graph: HatchyKnowledgeGraph):
        """Process equipment data."""
        df = pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            item_data = {
                'name': row['Name'],
                'type': row.get('Type', 'equipment'),
                'description': row.get('Description', ''),
                'attributes': {
                    'rarity': row.get('Rarity', 'common'),
                    'element': row.get('Element', None)
                }
            }
            
            entity_id = graph.add_entity(
                name=item_data['name'],
                entity_type='item',
                attributes=item_data
            ) 