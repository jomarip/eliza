from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class Character(BaseModel):
    """Character model for AI agents."""
    name: str
    role: str
    personality: List[str]
    background: str
    speaking_style: List[str]
    knowledge_domains: Optional[List[str]] = None
    
    def get_system_prompt(self) -> str:
        """Generate system prompt for character."""
        return f"""You are {self.name}, {self.role}.

Background:
{self.background}

Your personality traits:
{self._format_list(self.personality)}

Your speaking style:
{self._format_list(self.speaking_style)}

Knowledge domains: {', '.join(self.knowledge_domains or [])}

Always stay in character and maintain consistency with the Hatchyverse lore.
"""

    def _format_list(self, items: List[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    def respond(self, query: str, context: Dict[str, Any], history: Optional[List] = None) -> Dict[str, Any]:
        """Generate in-character response."""
        # Format context for response
        formatted_context = self._format_context(context)
        
        # Build response using character traits
        response = {
            'content': self._generate_content(query, formatted_context, history),
            'confidence': self._calculate_confidence(context),
            'character_traits_used': self._get_relevant_traits(query)
        }
        
        return response

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for response."""
        sections = []
        
        if context.get('entities'):
            sections.append("\nRelevant Entities:")
            for entity in context['entities']:
                sections.append(f"- {entity['name']} ({entity['entity_type']})")
                if 'attributes' in entity:
                    for k, v in entity['attributes'].items():
                        sections.append(f"  {k}: {v}")
        
        if context.get('relationships'):
            sections.append("\nRelationships:")
            for rel in context['relationships']:
                sections.append(
                    f"- {rel['source']['name']} {rel['type']} {rel['target']['name']}"
                )
        
        return "\n".join(sections) 