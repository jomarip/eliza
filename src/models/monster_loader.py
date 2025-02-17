from typing import Dict, Any, List
from pathlib import Path
import pandas as pd
import logging
from .knowledge_graph import HatchyKnowledgeGraph

logger = logging.getLogger(__name__)

class MonsterLoader:
    """Loads and processes monster data into the knowledge graph."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
    def load(self, graph: HatchyKnowledgeGraph) -> None:
        """Load monster data into the knowledge graph."""
        try:
            # Load Gen1 monsters
            gen1_path = self.data_dir / "Hatchy - Monster Data - gen 1.csv"
            if gen1_path.exists():
                self._process_monster_csv(gen1_path, graph, generation=1)
                
            # Load Gen2 monsters
            gen2_path = self.data_dir / "Hatchy - Monster Data - gen 2.csv"
            if gen2_path.exists():
                self._process_monster_csv(gen2_path, graph, generation=2)
                
            # Load Gen3 monsters
            gen3_path = self.data_dir / "Gen3 List - Asset list.csv"
            if gen3_path.exists():
                self._process_monster_csv(gen3_path, graph, generation=3)
                
        except Exception as e:
            logger.error(f"Error loading monster data: {str(e)}")
            raise
            
    def _process_monster_csv(self, file_path: Path, graph: HatchyKnowledgeGraph, generation: int):
        """Process a monster CSV file and add to graph."""
        df = pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            monster_data = {
                'name': row['Name'],
                'element': row['Element'],
                'description': row['Description'],
                'generation': generation,
                'attributes': {
                    'height': row.get('Height', 0),
                    'weight': row.get('Weight', 0),
                    'evolution_stage': self._determine_evolution_stage(row)
                }
            }
            
            # Add to graph
            entity_id = graph.add_entity(
                name=monster_data['name'],
                entity_type='monster',
                attributes=monster_data
            )
            
            # Add element relationship
            graph.add_relationship(
                entity_id,
                monster_data['element'].lower(),
                'has_element'
            )
            
    def _determine_evolution_stage(self, row: pd.Series) -> int:
        """Determine evolution stage from monster data."""
        name = row['Name'].lower()
        if any(term in name for term in ['baby', 'egg', 'seed']):
            return 1
        elif any(term in name for term in ['teen', 'juvenile']):
            return 2
        return 3 