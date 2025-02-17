from langchain_openai import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from fastapi import FastAPI, HTTPException, APIRouter, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from ..models.lore_validator import LoreValidator
from ..models.chatbot import LoreChatbot
from ..data.data_loader import DataLoader
import logging
from ..models.enhanced_chatbot import EnhancedChatbot
from ..models.knowledge_graph import HatchyKnowledgeGraph
from pathlib import Path
from ..models.lorekeeper import LorekeeperAgent
from ..config.model_providers import ACTIVE_PROVIDERS, PROVIDER_CONFIGS
from ..models.timeline_analyzer import TimelineAnalyzer
from ..models.political_engine import PoliticalEngine
from ..models.evolution_mapper import EvolutionMapper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app and routers
app = FastAPI(
    title="Hatchyverse Lore Chatbot",
    description="An AI-powered chatbot for exploring and contributing to Hatchyverse lore",
    version="1.0.0"
)

# Define routers
router = APIRouter(prefix="/api/v1")
hatchy_router = APIRouter(prefix="/hatchyverse")

# Add routers to app
app.include_router(router)
app.include_router(hatchy_router)

# Initialize components
data_dir = os.getenv("DATA_DIR", "./data")
model_provider = os.getenv("MODEL_PROVIDER", "openai")

# Get provider-specific model names
model_names = {
    "openai": os.getenv("OPENAI_MODEL_NAME", "gpt-4-0125-preview"),
    "anthropic": os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-sonnet-20240229"),
    "deepseek": os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
}

# Get provider-specific embedding models
embedding_models = {
    "openai": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
}

model_name = model_names.get(model_provider)
if not model_name:
    raise ValueError(f"No model name configured for provider: {model_provider}")

vector_store_path = os.getenv("VECTOR_STORE_PATH", "./data/vector_store")

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    chat_history: Optional[List[str]] = None

class LoreSubmission(BaseModel):
    content: str
    entity_type: str
    name: str
    element: Optional[str] = None
    metadata: Optional[dict] = None

class QueryRequest(BaseModel):
    """Model for complex query requests."""
    filters: Dict[str, Any]
    include_evolution: bool = False
    timespan: Optional[Dict[str, str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "filters": {
                    "type": ["monster", "faction"],
                    "generation": 3,
                    "region": "Omniterra"
                },
                "include_evolution": True,
                "timespan": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                }
            }
        }

# Global variables for components
chatbot = None
validator = None
timeline_analyzer = None
political_engine = None
evolution_mapper = None

# Add to existing imports
hatchy_router = APIRouter()

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    try:
        # Verify required configurations
        required_configs = [
            "OPENAI_API_KEY",
            "OPENAI_MODEL_NAME",
            "DATA_DIR",
            "VECTOR_STORE_PATH"
        ]
        
        missing_configs = [
            config for config in required_configs 
            if not os.getenv(config)
        ]
        
        if missing_configs:
            raise ValueError(
                f"Missing required configurations: {', '.join(missing_configs)}"
            )
            
        global chatbot, validator, timeline_analyzer, political_engine, evolution_mapper
        
        # Initialize OpenAI embeddings
        embeddings = OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        )
        
        # Initialize validator
        validator = LoreValidator(embeddings)
        
        # Load existing data
        loader = DataLoader(data_dir)
        entities = loader.load_all_data()
        
        # Build knowledge base
        validator.build_knowledge_base(entities)
        
        # Initialize chatbot
        chatbot = LoreChatbot(
            validator=validator,
            llm_client=llm_client
        )
        
        # Load knowledge graph
        graph_path = Path("knowledge_graphs/knowledge_graph_latest.json")
        app.state.knowledge_graph = HatchyKnowledgeGraph.load(graph_path)
        
        # Initialize OpenAI LLM client
        llm_client = ChatOpenAI(
            model_name=os.getenv("OPENAI_MODEL_NAME"),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize Lorekeeper
        app.state.lorekeeper = LorekeeperAgent(
            knowledge_graph=app.state.knowledge_graph,
            llm_client=llm_client
        )
        
        # Initialize additional components
        timeline_analyzer = TimelineAnalyzer(app.state.knowledge_graph)
        political_engine = PoliticalEngine(app.state.knowledge_graph)
        evolution_mapper = EvolutionMapper(app.state.knowledge_graph)
        
        logger.info("All components initialized successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.post("/chat")
async def chat_endpoint(message: ChatMessage):
    """
    Handle chat messages.
    
    Args:
        message: ChatMessage object containing the user's message and optional chat history
        
    Returns:
        Dict containing the chatbot's response
    """
    try:
        if not chatbot:
            raise HTTPException(status_code=503, detail="Chatbot not initialized")
            
        response = chatbot.generate_response(
            message.message,
            message.chat_history
        )
        
        return {
            "response": response["response"],
            "validation": response["validation"]
        }
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit")
async def submit_lore(submission: LoreSubmission):
    """
    Handle new lore submissions.
    
    Args:
        submission: LoreSubmission object containing the new lore content
        
    Returns:
        Dict containing validation results and feedback
    """
    try:
        if not validator:
            raise HTTPException(status_code=503, detail="Validator not initialized")
            
        # Format submission for validation
        formatted_submission = f"""
        Name: {submission.name}
        Type: {submission.entity_type}
        Element: {submission.element or 'N/A'}
        Description: {submission.content}
        """
        
        # Check for conflicts
        validation = validator.check_conflict(formatted_submission)
        
        # Process through chatbot for detailed feedback
        response = chatbot.generate_response(
            f"[SUBMIT]{formatted_submission}",
            []
        )
        
        return {
            "response": response["response"],
            "validation": validation,
            "accepted": len(validation["conflicts"]) == 0
        }
        
    except Exception as e:
        logger.error(f"Error in submit endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "chatbot": chatbot is not None,
            "validator": validator is not None
        }
    }

@hatchy_router.post("/lore/submit")
async def submit_lore_entry(payload: dict):
    """Process Hatchyverse lore submissions"""
    # Implementation from Lorebot.md validation process
    return {"status": "received", "validation_hash": payload['content_hash']}

@hatchy_router.get("/lore/query")
async def query_knowledge_graph(query: str):
    """Query Hatchyverse knowledge graph"""
    graph = HatchyKnowledgeGraph.load()
    return graph.query(query)

@hatchy_router.post("/lore/vote")
async def submit_vote(payload: dict):
    """Handle community voting on lore entries"""
    # Integrates with LoreSubmission.move contract
    return {"voting_status": "processed"}

# Add Hatchyverse endpoints to existing router
@app.post("/hatchyverse/submit")
async def submit_lore_entry(payload: dict):
    """Process Hatchyverse lore submissions"""
    # Implementation from Lorebot.md validation process
    return {"status": "received", "validation_hash": payload['content_hash']}

@app.get("/hatchyverse/query")
async def query_knowledge_graph(query: str):
    """Query Hatchyverse knowledge graph"""
    graph = HatchyKnowledgeGraph.load()
    return graph.query(query)

@app.post("/hatchyverse/vote")
async def submit_vote(payload: dict):
    """Handle community voting on lore entries"""
    # Integrates with LoreSubmission.move contract
    return {"voting_status": "processed"}

@router.post("/query")
async def complex_query(request: QueryRequest):
    """Handle multi-faceted queries across canon."""
    try:
        response = {
            'monsters': app.state.knowledge_graph.query_monsters(request.filters),
            'locations': app.state.knowledge_graph.get_related_entities(
                request.filters.get('location', ''),
                max_depth=2
            ),
            'timeline': timeline_analyzer.get_events(request.timespan) if request.timespan else [],
            'conflicts': political_engine.detect_conflicts(request.filters)
        }
        
        # Add evolutionary context if needed
        if request.include_evolution:
            response['evolution_chains'] = evolution_mapper.get_chains(
                response['monsters']
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing complex query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@hatchy_router.post("/validate")
async def validate_entry(payload: dict):
    """Validate lore entry against knowledge graph"""
    graph = app.state.knowledge_graph
    return {
        "conflicts": graph.find_conflicts(payload['content']),
        "suggestions": graph.generate_suggestions(payload['content'])
    } 