from pathlib import Path
import pandas as pd
from .knowledge_graph import HatchyKnowledgeGraph
import logging

logger = logging.getLogger(__name__)

class EvolutionLoader:
    """Loads evolution chain data into the knowledge graph."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
    def load(self, graph: HatchyKnowledgeGraph) -> None:
        """Load evolution data into the knowledge graph."""
        try:
            # Process evolution data from monster files
            gen_files = {
                1: self.data_dir / "Hatchy - Monster Data - gen 1.csv",
                2: self.data_dir / "Hatchy - Monster Data - gen 2.csv",
                3: self.data_dir / "Gen3 List - Asset list.csv"
            }
            
            for gen, file_path in gen_files.items():
                if file_path.exists():
                    self._process_evolution_data(file_path, graph, gen)
                    
        except Exception as e:
            logger.error(f"Error loading evolution data: {str(e)}")
            raise
            
    def _process_evolution_data(self, file_path: Path, graph: HatchyKnowledgeGraph, generation: int):
        """Process evolution chains from monster data."""
        df = pd.read_csv(file_path)
        
        # Group by evolution family
        for _, row in df.iterrows():
            if 'Evolution' in row:
                base_form = row['Name']
                evolved_form = row['Evolution']
                
                # Add evolution relationship
                graph.add_relationship(
                    source=base_form,
                    target=evolved_form,
                    relationship_type='evolves_into'
                ) 