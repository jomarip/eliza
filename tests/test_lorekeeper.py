import pytest
from scripts.init_lorekeeper import initialize_lorekeeper
from pathlib import Path

def test_character_initialization():
    """Test Lorekeeper character registration"""
    try:
        initialize_lorekeeper()
        config_path = Path("characters/lorekeeper_eliza.json")
        assert config_path.exists(), "Character config missing"
        
        data_dirs = [
            Path("data/lore/official_canon"),
            Path("data/lore/community_vetted")
        ]
        for d in data_dirs:
            assert d.exists(), f"Data directory {d} not found"
            
    except Exception as e:
        pytest.fail(f"Initialization failed: {str(e)}")

def test_knowledge_loading():
    """Test loading of Hatchyverse lore data"""
    from src.data.enhanced_loader import EnhancedDataLoader
    from src.models.knowledge_graph import HatchyKnowledgeGraph
    
    try:
        graph = HatchyKnowledgeGraph()
        loader = EnhancedDataLoader(graph)
        
        # Load test data
        test_files = [
            "data/lore/official_canon/Hatchy World _ world design.txt",
            "data/lore/official_canon/chaos_saga.txt"
        ]
        
        for f in test_files:
            loader.load_text_data(f)
            
        assert len(graph.entities) > 0, "No entities loaded"
        assert len(graph.relationships) > 0, "No relationships found"
        
    except Exception as e:
        pytest.fail(f"Data loading failed: {str(e)}")