import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json
from src.models.knowledge_graph import HatchyKnowledgeGraph
from src.models.base_loader import BaseLoader
from src.models.lorekeeper import LorekeeperAgent
from src.models.llm import get_llm_client

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()

def main():
    # Initialize components
    data_dir = Path("data")
    loader = BaseLoader(data_dir)
    llm_client = get_llm_client()
    
    print("Loading Hatchyverse knowledge...")
    
    # Load all data
    elements = loader.initialize_core_elements()
    for element in elements:
        loader.knowledge_graph.add_entity(**element)
    
    # Load structured data
    loader.load_monsters()
    loader.load_factions()
    
    # Load text content
    for text_file in (data_dir/"official_canon").glob("*.txt"):
        entities = loader.load_text_content(text_file)
        for entity in entities:
            loader.knowledge_graph.add_entity(**entity)
    
    # Initialize Lorekeeper
    lorekeeper = LorekeeperAgent(
        knowledge_graph=loader.knowledge_graph,
        llm_client=llm_client
    )
    
    # Test comprehensive interaction
    conversation = []
    test_scenarios = [
        {
            "category": "World Overview",
            "questions": [
                "Tell me about the Hatchyverse and its core elements.",
                "What are the major regions and their characteristics?",
                "How do the different elements interact with each other?"
            ]
        },
        {
            "category": "Monsters and Evolution",
            "questions": [
                "What types of Hatchies exist in the Fire element category?",
                "How does evolution work in the Hatchyverse?",
                "Tell me about some of the most powerful Hatchies."
            ]
        },
        {
            "category": "Politics and Factions",
            "questions": [
                "What are the major factions in the Hatchyverse?",
                "How do these factions interact with each other?",
                "Tell me about the political landscape."
            ]
        }
    ]
    
    # Run tests and save results
    results = []
    
    print("\nBeginning Lorekeeper interaction test...\n")
    
    for scenario in test_scenarios:
        print(f"\n=== Testing {scenario['category']} ===\n")
        
        for question in scenario['questions']:
            print(f"\nUser: {question}")
            
            response = lorekeeper.generate_response(question, conversation)
            print(f"\nLorekeeper: {response['content']}")
            
            if 'entities' in response:
                print("\nRelevant Knowledge:")
                for entity in response['entities'][:3]:
                    print(f"- {entity['name']} ({entity['entity_type']})")
            
            # Save interaction
            results.append({
                'category': scenario['category'],
                'question': question,
                'response': response,
                'entities_referenced': len(response.get('entities', [])),
                'relationships_found': len(response.get('relationships', []))
            })
            
            # Update conversation history
            conversation.extend([
                {'role': 'user', 'content': question},
                {'role': 'assistant', 'content': response['content']}
            ])
    
    # Save results
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "lorekeeper_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nTest complete! Results saved to test_results/lorekeeper_test_results.json")

if __name__ == "__main__":
    main() 