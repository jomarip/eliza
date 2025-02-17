from pathlib import Path
import pandas as pd
from .knowledge_graph import HatchyKnowledgeGraph
import logging

logger = logging.getLogger(__name__)

class WorldLoader:
    """Loads world and location data into the knowledge graph."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
    def load(self, graph: HatchyKnowledgeGraph) -> None:
        """Load world data into the knowledge graph."""
        try:
            # Load world design data
            world_path = self.data_dir / "Hatchy World _ world design.txt"
            if world_path.exists():
                self._process_world_design(world_path, graph)
                
            # Load location data
            locations_path = self.data_dir / "Hatchipedia - nations and politics.csv"
            if locations_path.exists():
                self._process_locations(locations_path, graph)
                
        except Exception as e:
            logger.error(f"Error loading world data: {str(e)}")
            raise
            
    def _process_world_design(self, file_path: Path, graph: HatchyKnowledgeGraph):
        """Process world design document."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Add world entity
        world_data = {
            'name': 'Omniterra',
            'description': 'The world of Hatchyverse',
            'attributes': {
                'content': content
            }
        }
        
        graph.add_entity(
            name=world_data['name'],
            entity_type='world',
            attributes=world_data
        )
            
    def _process_locations(self, file_path: Path, graph: HatchyKnowledgeGraph):
        """Process location data from nations file."""
        df = pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            if pd.notna(row.get('Nation Name')):
                location_data = {
                    'name': row['Nation Name'],
                    'description': row.get('Description', ''),
                    'attributes': {
                        'themes': row.get('Themes', ''),
                        'political_system': row.get('Government system', '')
                    }
                }
                
                entity_id = graph.add_entity(
                    name=location_data['name'],
                    entity_type='location',
                    attributes=location_data
                ) 