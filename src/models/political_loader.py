from pathlib import Path
import pandas as pd
from .knowledge_graph import HatchyKnowledgeGraph
import logging

logger = logging.getLogger(__name__)

class PoliticalLoader:
    """Loads political and faction data into the knowledge graph."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
    def load(self, graph: HatchyKnowledgeGraph) -> None:
        """Load political data into the knowledge graph."""
        try:
            # Load faction data
            factions_path = self.data_dir / "Hatchipedia - Factions and groups.csv"
            if factions_path.exists():
                self._process_factions(factions_path, graph)
                
            # Load nations data
            nations_path = self.data_dir / "Hatchipedia - nations and politics.csv"
            if nations_path.exists():
                self._process_nations(nations_path, graph)
                
        except Exception as e:
            logger.error(f"Error loading political data: {str(e)}")
            raise
            
    def _process_factions(self, file_path: Path, graph: HatchyKnowledgeGraph):
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            faction_data = {
                'name': row['Name'],
                'description': row['Subplot and Relationship to Main Plot'],
                'agenda': row['Agenda/Motivations'],
                'type': row['Faction']
            }
            
            entity_id = graph.add_entity(
                name=faction_data['name'],
                entity_type='faction',
                attributes=faction_data
            ) 