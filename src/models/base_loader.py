from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path
import logging
from .knowledge_graph import HatchyKnowledgeGraph

logger = logging.getLogger(__name__)

class BaseLoader:
    """Base data loader without AI dependencies."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.official_dir = self.data_dir/"official_canon"
        self.knowledge_graph = HatchyKnowledgeGraph()
        
        # Define file paths
        self.file_paths = {
            'monsters': self.official_dir/"Hatchy - Monster Data - gen 1.csv",
            'factions': self.official_dir/"Hatchipedia - Factions and groups.csv",
            'champions': self.official_dir/"Hatchipedia - famous champions.csv",
            'nations': self.official_dir/"Hatchipedia - nations and politics.csv"
        }