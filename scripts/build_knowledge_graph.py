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
from src.models.base_loader import BaseLoader

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data", help="Data directory path")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild graph")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    logger.info("Initializing knowledge graph...")
    loader = BaseLoader(args.data_dir)
    
    # Load core elements first
    elements = loader.initialize_core_elements()
    for element in elements:
        loader.knowledge_graph.add_entity(**element)
        
    # Load structured data
    logger.info("Loading structured data...")
    loader.load_monsters()
    loader.load_factions()
    
    # Load text content
    logger.info("Loading text content...")
    for text_file in (Path(args.data_dir)/"official_canon").glob("*.txt"):
        entities = loader.load_text_content(text_file)
        for entity in entities:
            loader.knowledge_graph.add_entity(**entity)
    
    # Process world design document
    logger.info("Processing world design...")
    world_file = Path(args.data_dir)/"official_canon"/"Hatchy World _ world design.txt"
    if world_file.exists():
        world_entities = loader.load_text_content(world_file)
        for entity in world_entities:
            loader.knowledge_graph.add_entity(**entity)
    
    # Get statistics
    stats = loader.knowledge_graph.get_statistics()
    logger.info(f"Knowledge graph statistics: {json.dumps(stats, indent=2)}")

if __name__ == '__main__':
    # Set up paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    output_dir = project_root / "knowledge_graphs"
    
    # Build graph
    main() 