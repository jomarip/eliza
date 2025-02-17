from typing import Dict, Any, Optional, List
from .enhanced_chatbot import EnhancedChatbot
from .knowledge_graph import HatchyKnowledgeGraph
from .character import Character
from .prompts import LOREKEEPER_PROMPT_TEMPLATE, LORE_VALIDATION_TEMPLATE, get_prompt_template, ELEMENT_EMOJIS
import logging

logger = logging.getLogger(__name__)

class LorekeeperAgent(EnhancedChatbot):
    """Lorekeeper agent for managing Hatchyverse knowledge."""
    
    CHARACTER_TEMPLATE = {
        "name": "The Lorekeeper",
        "role": "Guardian of Hatchyverse Knowledge",
        "personality": [
            "Wise and deeply knowledgeable about the Hatchyverse",
            "Enthusiastic about sharing lore and connections",
            "Careful to maintain canonical accuracy",
            "Patient in explaining complex relationships",
            "Scholarly yet approachable"
        ],
        "background": """
        I am the Lorekeeper, custodian of all knowledge in the Hatchyverse. I have 
        witnessed the evolution of Hatchies across generations, documented the rise 
        and fall of factions, and preserved the rich tapestry of our world's history.
        My purpose is to share this knowledge while ensuring its accuracy and preservation.
        """,
        "speaking_style": [
            "Uses rich, descriptive language",
            "References specific examples and connections",
            "Balances academic precision with accessibility",
            "Incorporates appropriate Hatchyverse terminology",
            "Maintains an engaging narrative flow"
        ],
        "knowledge_domains": [
            "Hatchie Species and Evolution",
            "Elemental Systems",
            "Faction Politics and History",
            "World Geography and Regions",
            "Cultural Traditions and Practices"
        ]
    }

    def __init__(self, knowledge_graph: HatchyKnowledgeGraph, llm_client=None):
        """Initialize Lorekeeper with character and knowledge."""
        character = Character(**self.CHARACTER_TEMPLATE)
        super().__init__(character=character, llm_client=llm_client)
        self.graph = knowledge_graph

    def generate_response(self, query: str, history: Optional[List] = None) -> Dict[str, Any]:
        """Generate a response to a query using the knowledge graph and character."""
        try:
            # Get context from knowledge graph
            context = self._get_relevant_context(query)
            
            # Determine query type
            query_type = self._determine_query_type(query)
            
            # Get appropriate template
            template = get_prompt_template(query_type)
            
            # Format prompt with additional parameters if needed
            prompt_params = {
                'query': query,
                'context': self._format_context(context),
                'history': self._format_history(history)
            }
            
            # Add element-specific parameters
            if query_type == 'element':
                element = self._extract_element(query)
                prompt_params.update({
                    'element': element,
                    'element_emoji': ELEMENT_EMOJIS.get(element.lower(), '❓')
                })
            
            # Add faction-specific parameters
            elif query_type in ['political', 'faction_compare']:
                factions = self._extract_factions(query)
                prompt_params.update(factions)
            
            # Generate response
            response = self.llm_client.generate(template.format(**prompt_params))
            
            return {
                'content': response,
                'entities': context['entities'],
                'relationships': context['relationships'],
                'sources': context.get('sources', []),
                'query_type': query_type
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                'content': "I apologize, but I seem to be having trouble accessing that information.",
                'error': str(e)
            }

    def validate_lore(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Validate new lore against existing knowledge."""
        # Get relevant context
        context = self._get_relevant_context(submission['content'])
        
        # Format validation prompt
        prompt = LORE_VALIDATION_TEMPLATE.format(
            submission=submission['content'],
            context=self._format_context(context)
        )
        
        # Generate validation
        validation = self.llm_client.generate(prompt)
        
        return {
            'validation': validation,
            'context': context,
            'confidence': self._calculate_confidence(context)
        }

    def _get_relevant_context(self, query: str) -> Dict[str, Any]:
        """Get relevant context from knowledge graph."""
        # Search for relevant entities
        entities = self.graph.search_entities(query, limit=5)
        
        # Get relationships for context
        relationships = []
        for entity in entities:
            relationships.extend(
                self.graph.get_related_entities(entity['id'], max_depth=2)
            )
            
        # Get any relevant lore text
        sources = self.graph.get_source_documents(query)
        
        return {
            'entities': entities,
            'relationships': relationships,
            'sources': sources
        }

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for response."""
        formatted = []
        
        # Add entity information
        if context['entities']:
            formatted.append("\nRelevant Entities:")
            for entity in context['entities']:
                formatted.append(f"- {entity['name']} ({entity['entity_type']})")
                
        # Add relationship information
        if context['relationships']:
            formatted.append("\nRelated Information:")
            for rel in context['relationships']:
                formatted.append(
                    f"- {rel['source']['name']} {rel['type']} {rel['target']['name']}"
                )
                
        return "\n".join(formatted)

    def _format_history(self, history: Optional[List] = None) -> str:
        """Format conversation history for prompt."""
        if not history:
            return ""
        return "\n".join(f"{i+1}. {message}" for i, message in enumerate(history))

    def _calculate_confidence(self, context: Dict[str, Any]) -> float:
        """Calculate confidence based on context."""
        # This is a placeholder implementation. In a real-world scenario, you might
        # want to implement a more robust confidence calculation based on the context.
        return 0.85  # Default confidence

    def validate_submission(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a lore submission against existing knowledge."""
        validation_result = self.graph.validate_lore(submission)
        
        response = self.templates['validation'].format(
            consistency=self._format_consistency_check(validation_result),
            improvements=self._format_improvements(validation_result),
            assessment=validation_result['assessment']
        )
        
        return {
            'content': response,
            'valid': validation_result['valid'],
            'issues': validation_result['issues']
        }

    def _format_consistency_check(self, validation: Dict[str, Any]) -> str:
        """Format consistency check results."""
        checks = []
        for check in validation['consistency_checks']:
            status = "✓" if check['passed'] else "✗"
            checks.append(f"{status} {check['description']}")
        return "\n".join(checks)

    def _format_improvements(self, validation: Dict[str, Any]) -> str:
        """Format improvement suggestions."""
        if not validation['suggestions']:
            return "No improvements needed."
            
        return "\n".join(f"- {suggestion}" for suggestion in validation['suggestions'])

    def _determine_query_type(self, query: str) -> str:
        """Determine the type of query for appropriate prompt selection."""
        query_lower = query.lower()
        
        if any(element in query_lower for element in ELEMENT_EMOJIS.keys()):
            return 'element'
        elif any(term in query_lower for term in ['evolve', 'evolution', 'transform']):
            return 'evolution'
        elif any(term in query_lower for term in ['region', 'location', 'area', 'where']):
            return 'world'
        elif any(term in query_lower for term in ['faction', 'politics', 'alliance']):
            return 'political'
        elif 'compare' in query_lower and 'faction' in query_lower:
            return 'faction_compare'
        
        return 'base'

    def _extract_element(self, query: str) -> str:
        """Extract element from query."""
        query_lower = query.lower()
        for element in ELEMENT_EMOJIS.keys():
            if element in query_lower:
                return element
        return "unknown"

    def _extract_factions(self, query: str) -> Dict[str, str]:
        """Extract factions from query."""
        query_lower = query.lower()
        factions = {}
        for term in ['faction', 'politics', 'alliance']:
            if term in query_lower:
                factions[term] = self._extract_element(query)
        return factions

    def _format_consistency_check(self, validation: Dict[str, Any]) -> str:
        """Format consistency check results."""
        checks = []
        for check in validation['consistency_checks']:
            status = "✓" if check['passed'] else "✗"
            checks.append(f"{status} {check['description']}")
        return "\n".join(checks)

    def _format_improvements(self, validation: Dict[str, Any]) -> str:
        """Format improvement suggestions."""
        if not validation['suggestions']:
            return "No improvements needed."
            
        return "\n".join(f"- {suggestion}" for suggestion in validation['suggestions']) 