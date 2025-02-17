import sys
import os

# Add Eliza's core directory to Python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../eliza/packages/core/src'))
)

from character_manager import CharacterManager  # Actual path in Eliza's codebase
from pathlib import Path

def initialize_lorekeeper():
    config_path = Path("characters/lorekeeper_eliza.json")
    data_dirs = [
        Path("data/lore/official_canon"),
        Path("data/lore/community_vetted")
    ]
    
    CharacterManager.register_character(
        config_path=config_path,
        required_dirs=data_dirs,
        knowledge_bases=["hatchyverse_core", "community_lore"]
    )
    
    print("Lorekeeper initialized with:")
    print(f"- {len(list(data_dirs[0].glob('*.json')))} core documents")
    print(f"- {len(list(data_dirs[1].glob('*.json')))} community documents")

if __name__ == "__main__":
    initialize_lorekeeper() 