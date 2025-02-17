"""Script to build and initialize the Hatchyverse knowledge graph."""

import os
import sys
import logging
from pathlib import Path
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import argparse

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.models.knowledge_graph import HatchyKnowledgeGraph
from src.models.enhanced_loader import EnhancedDataLoader, EnhancedLoader
from src.models.monster_loader import MonsterLoader
from src.models.political_loader import PoliticalLoader
from src.models.evolution_loader import EvolutionLoader
from src.models.item_loader import ItemLoader
from src.models.world_loader import WorldLoader

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

def build_hatchyverse_graph(data_dir: Path) -> HatchyKnowledgeGraph:
    graph = HatchyKnowledgeGraph()
    
    # Load core datasets
    loaders = {
        'monsters': MonsterLoader(data_dir/'official_canon'),
        'factions': PoliticalLoader(data_dir/'political'),
        'evolution': EvolutionLoader(data_dir/'generations'),
        'items': ItemLoader(data_dir/'equipment'),
        'locations': WorldLoader(data_dir/'world')
    }
    
    # Parallel loading with validation
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(loader.load, graph): loader 
                  for loader in loaders.values()}
        for future in as_completed(futures):
            loader = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error loading {loader}: {str(e)}")
    
    # Cross-link entities
    graph.create_relationship(
        'Monster', 'Location', 'habitat', 
        lambda m,l: m.element in l.primary_elements
    )
    
    graph.create_relationship(
        'Item', 'Monster', 'equippable_by',
        lambda i,m: i.required_level <= m.evolution_stage
    )
    
    return graph

def build_knowledge_graph(data_dir: Path, output_dir: Path) -> None:
    """Build and save the knowledge graph."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        logger.info("Initializing knowledge graph...")
        knowledge_graph = HatchyKnowledgeGraph()
        
        # Initialize OpenAI LLM client using correct env vars
        llm_client = ChatOpenAI(
            model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-4-1106-preview"),  # Changed to match .env
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize data loader with LLM
        data_loader = EnhancedDataLoader(
            knowledge_graph=knowledge_graph,
            llm_client=llm_client
        )
        
        # Set data directory
        data_loader.set_data_directory(data_dir)
        
        # Load all data
        logger.info("Loading data into knowledge graph...")
        loaded_entities = data_loader.load_all_data()
        
        # Get statistics
        stats = knowledge_graph.get_statistics()
        logger.info(f"Knowledge graph statistics: {json.dumps(stats, indent=2)}")
        
        # Export graph
        logger.info("Exporting knowledge graph...")
        graph_data = knowledge_graph.export_to_dict()
        
        # Create timestamp for versioning
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"knowledge_graph_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2)
            
        # Update symlink with proper error handling
        latest_link = output_dir / "knowledge_graph_latest.json"
        try:
            if latest_link.exists():
                latest_link.unlink()
            latest_link.symlink_to(output_file.name)  # Use relative path
            logger.info(f"Latest symlink updated: {latest_link}")
        except OSError as e:
            logger.warning(f"Could not create symlink: {e}. Continuing anyway...")
            
        logger.info(f"Knowledge graph saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error building knowledge graph: {str(e)}")
        raise

def load_experimental_data(graph, data_dir):
    exp_dir = data_dir / 'unstructured'
    if exp_dir.exists():
        logger.info("Loading experimental data...")
        graph.add_context_tag('experimental')
        
        # Load all supported formats
        for file in exp_dir.glob('**/*'):
            if file.suffix[1:] in SUPPORTED_EXTENSIONS:
                entities = load_file(file)
                graph.bulk_add(entities, source='experimental')

def main():
    """Build and save the knowledge graph."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data", help="Data directory path")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild graph")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    logger.info("Initializing knowledge graph...")
    graph = HatchyKnowledgeGraph()

    # Initialize loader with correct data dir
    loader = EnhancedLoader(args.data_dir)
    
    logger.info("Loading data into knowledge graph...")
    
    # Load core elements first
    elements = loader.initialize_core_elements()
    for element in elements:
        # Elements are already formatted with type
        graph.add_entity(
            name=element['name'],
            entity_type=element['type'],
            attributes=element['attributes']
        )
        
    # Load monsters
    monsters = loader.load_monsters()
    for monster in monsters:
        # Monsters are formatted with type
        graph.add_entity(
            name=monster['name'],
            entity_type=monster['type'],
            attributes={
                'element': monster['element'],
                'description': monster['description'],
                **monster['attributes']  # Include height, weight, generation
            }
        )
        
    # Load factions
    factions = loader.load_factions()
    for faction in factions:
        graph.add_entity(
            name=faction['name'],
            entity_type=faction['type'],
            attributes={
                'description': faction['description'],
                **faction['attributes']  # Include agenda, symbol, locations
            }
        )
        
    # Load champions
    champions = loader.load_champions() 
    for champion in champions:
        graph.add_entity(
            name=champion['name'],
            entity_type=champion['type'],
            attributes={
                'description': champion['description'],
                **champion['attributes']  # Include subplot, nation, agenda
            }
        )
        
    # Load nations
    nations = loader.load_nations()
    for nation in nations:
        graph.add_entity(
            name=nation['name'],
            entity_type=nation['type'],
            attributes={
                'description': nation['description'],
                **nation['attributes']  # Include themes, culture, conflict
            }
        )
        
    # Get statistics
    stats = graph.get_statistics()
    logger.info(f"Knowledge graph statistics: {json.dumps(stats, indent=2)}")
    
    # Export graph
    logger.info("Exporting knowledge graph...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "knowledge_graphs"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"knowledge_graph_{timestamp}.json"
    latest_link = output_dir / "knowledge_graph_latest.json"
    
    # Save graph data
    graph_data = graph.export_to_dict()
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2)
        
    # Update symlink
    try:
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(output_file.name)
    except OSError as e:
        logger.warning(f"Could not create symlink: {e}. Continuing anyway...")
        
    logger.info(f"Knowledge graph saved to {output_file}")

if __name__ == '__main__':
    # Set up paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    output_dir = project_root / "knowledge_graphs"
    
    # Build graph
    main() 