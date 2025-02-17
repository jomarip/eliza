from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import uuid
import re
from collections import defaultdict
import logging
import networkx as nx
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

class EntityData(BaseModel):
    """Validation model for entity data."""
    name: str = Field(..., min_length=1)
    entity_type: str = Field(..., min_length=1)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty or just whitespace")
        return v.strip()

    @validator('entity_type')
    def validate_type(cls, v):
        if not v.strip():
            raise ValueError("Entity type cannot be empty or just whitespace")
        return v.strip()

class HatchyKnowledgeGraph:
    """Core knowledge graph for Hatchyverse."""
    
    VALID_ENTITY_TYPES = {
        'monster', 'element', 'faction', 'champion', 'location', 
        'item', 'ability', 'evolution', 'nation'
    }
    
    VALID_RELATIONSHIPS = {
        'has_element': {'monster', 'location'},
        'evolves_from': {'monster'},
        'lives_in': {'monster', 'location'},
        'member_of': {'champion', 'faction'},
        'located_in': {'faction', 'location'},
        'controls': {'faction', 'location'},
        'allied_with': {'faction', 'nation'},
        'hostile_to': {'faction', 'nation'},
        'wields': {'champion', 'item'},
        'teaches': {'champion', 'ability'},
        'requires': {'evolution', 'item'}
    }

    def __init__(self):
        """Initialize the knowledge graph."""
        self.graph = nx.MultiDiGraph()
        self.entities = {}
        self.relationships = []
        self.indices = {
            'id': {},  # id -> entity
            'name': {},  # name -> id
            'type': defaultdict(set),  # type -> set(ids)
            'attribute': defaultdict(lambda: defaultdict(set)),  # attr -> value -> set(ids)
            'location': defaultdict(set),  # location -> set(ids)
            'element': defaultdict(set),  # element -> set(ids)
            'relationships': defaultdict(lambda: defaultdict(list))  # source_id -> type -> [target_ids]
        }
        
        # Initialize relationship registry
        self.relationship_registry = {
            'has_element': {'inverse': 'element_of', 'confidence_threshold': 0.9},
            'evolves_from': {'inverse': 'evolves_into', 'confidence_threshold': 0.9},
            'member_of': {'inverse': 'has_member', 'confidence_threshold': 0.8},
            'allied_with': {'inverse': 'allied_with', 'confidence_threshold': 0.8},
            'opposes': {'inverse': 'opposed_by', 'confidence_threshold': 0.8},
            'controls': {'inverse': 'controlled_by', 'confidence_threshold': 0.8},
            'commands': {'inverse': 'commanded_by', 'confidence_threshold': 0.8},
            'hatches_from': {'inverse': 'hatches_into', 'confidence_threshold': 0.9},
            'lives_in': {'inverse': 'habitat_of', 'confidence_threshold': 0.8},
            'belongs_to': {'inverse': 'owns', 'confidence_threshold': 0.8},
            'trades_with': {'inverse': 'trades_with', 'confidence_threshold': 0.8},
            'borders': {'inverse': 'borders', 'confidence_threshold': 0.9},
            'has_capital': {'inverse': 'capital_of', 'confidence_threshold': 0.9},
            'leads': {'inverse': 'led_by', 'confidence_threshold': 0.9},
            'serves': {'inverse': 'served_by', 'confidence_threshold': 0.8},
            'mentors': {'inverse': 'mentored_by', 'confidence_threshold': 0.9}
        }
        
        # Initialize core elements
        self.core_elements = {
            'fire', 'water', 'plant', 'void', 'light', 'dark',
            'electric', 'earth', 'air', 'metal', 'chaos', 'order',
            'both', 'lunar', 'solar'
        }
        self._init_core_elements()

    def _init_core_elements(self):
        """Initialize core elements with proper attributes."""
        for element in self.core_elements:
            try:
                element_name = element.capitalize()
                if not self.get_entity_by_name(element_name):
                    logger.debug(f"Creating core element: {element_name}")
                    
                    attributes = {
                        "name": element_name,
                        "symbol": self._get_element_symbol(element),
                        "is_core_element": True
                    }
                    
                    # Special handling for dual/special elements
                    if element == 'both':
                        attributes.update({
                            "combines": ["Light", "Dark"],
                            "is_dual_element": True
                        })
                    elif element in ['lunar', 'solar']:
                        attributes.update({
                            "related_to": "Dark" if element == 'lunar' else "Light",
                            "is_special_element": True
                        })
                    
                    self.add_entity(
                        name=element_name,
                        entity_type="element",
                        attributes=attributes,
                        metadata={'core_element': True}
                    )
            except Exception as e:
                logger.warning(f"Error creating core element {element}: {str(e)}")

    def _get_element_symbol(self, element: str) -> str:
        """Get symbol for element."""
        symbols = {
            'fire': '🔥', 'water': '💧', 'plant': '🌿',
            'void': '🌌', 'light': '✨', 'dark': '🌑',
            'electric': '⚡', 'earth': '🌍', 'air': '🌪️',
            'metal': '⚙️', 'chaos': '🌀', 'order': '⚖️',
            'both': '☯️', 'lunar': '🌙', 'solar': '☀️'
        }
        return symbols.get(element.lower(), '❓')

    def add_entity(self, name: str, entity_type: str, attributes: Dict[str, Any], 
                  metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add entity to graph with validation and relationship processing."""
        # Validate entity type
        if entity_type not in self.VALID_ENTITY_TYPES:
            raise ValueError(f"Invalid entity type: {entity_type}")
            
        entity_id = str(uuid.uuid4())
        entity = {
            'id': entity_id,
            'name': name,
            'entity_type': entity_type,
            'attributes': attributes or {},
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        
        # Store entity
        self.entities[entity_id] = entity
        self.graph.add_node(entity_id, **entity)
        
        # Update indices
        self.indices['id'][entity_id] = entity
        self.indices['name'][name.lower()] = entity_id
        self.indices['type'][entity_type].add(entity_id)
        
        # Process relationships
        self.process_relationships(entity_id, entity)
        
        return entity_id

    def add_relationship(self, source_id: str, target_id: str, relationship_type: str,
                        attributes: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Add relationship with validation."""
        try:
            if relationship_type not in self.relationship_registry:
                logger.warning(f"Invalid relationship type: {relationship_type}")
                return None
                
            if source_id not in self.entities or target_id not in self.entities:
                return None
                
            relationship_id = str(uuid.uuid4())
            relationship = {
                'id': relationship_id,
                'source': source_id,
                'target': target_id,
                'type': relationship_type,
                'attributes': attributes or {},
                'confidence': self.relationship_registry[relationship_type]['confidence_threshold']
            }
            
            # Add to graph
            self.graph.add_edge(source_id, target_id, 
                              key=relationship_id, **relationship)
            
            # Update indices
            self.indices['relationships'][relationship_type][source_id].append(relationship)
            
            # Add inverse relationship if defined
            inverse_type = self.relationship_registry[relationship_type].get('inverse')
            if inverse_type:
                self.indices['relationships'][inverse_type][target_id].append(relationship)
                
            return relationship_id
            
        except Exception as e:
            logger.error(f"Error adding relationship: {str(e)}")
            return None

    def get_related_entities(self, entity_id: str, relationship_type: Optional[str] = None,
                           max_depth: int = 1) -> List[Dict[str, Any]]:
        """Get related entities with depth control."""
        if entity_id not in self.entities:
            return []
            
        related = []
        visited = {entity_id}
        
        def traverse(current_id: str, depth: int):
            if depth > max_depth:
                return
                
            edges = self.graph.edges(current_id, data=True)
            for source, target, data in edges:
                next_id = target if source == current_id else source
                if next_id not in visited:
                    if not relationship_type or data['type'] == relationship_type:
                        related.append({
                            'entity': self.entities[next_id],
                            'relationship': data['type'],
                            'direction': 'outgoing' if source == current_id else 'incoming'
                        })
                        visited.add(next_id)
                        if depth < max_depth:
                            traverse(next_id, depth + 1)
                            
        traverse(entity_id, 1)
        return related

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        stats = {
            'total_entities': len(self.entities),
            'entity_types': {t: len(ids) for t, ids in self.indices['type'].items()},
            'total_relationships': self.graph.number_of_edges(),
            'relationship_types': defaultdict(int),
            'element_counts': defaultdict(int)
        }
        
        # Count relationships by type
        for _, _, data in self.graph.edges(data=True):
            stats['relationship_types'][data['type']] += 1
            
        # Count elements
        for entity in self.entities.values():
            if entity['entity_type'] == 'monster':
                element = entity['attributes'].get('element')
                if element:
                    stats['element_counts'][element] += 1
                    
        return dict(stats)

    def export_to_dict(self) -> Dict[str, Any]:
        """Export graph to dictionary format."""
        return {
            'entities': list(self.entities.values()),
            'relationships': [
                {
                    'source': s,
                    'target': t,
                    'type': d['type'],
                    'attributes': d.get('attributes', {})
                }
                for s, t, d in self.graph.edges(data=True)
            ],
            'statistics': self.get_statistics()
        }

    def get_entity_by_name(self, name: str, fuzzy_match: bool = False) -> Optional[Dict[str, Any]]:
        """Get entity by name with optional fuzzy matching."""
        if not name:
            return None
        
        name_lower = name.lower()
        
        # Try exact match first
        entity_id = self.indices['name'].get(name_lower)
        if entity_id:
            return self.entities[entity_id]
        
        # Try fuzzy matching if enabled
        if fuzzy_match:
            for entity_id, entity in self.entities.items():
                if name_lower in entity['name'].lower():
                    return entity
                
        return None

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all entities of a specific type."""
        return [self.entities[eid] for eid in self.indices['type'].get(entity_type, set())]

    def get_entities_by_element(self, element: str) -> List[Dict[str, Any]]:
        """Get all entities with a specific element."""
        return [self.entities[eid] for eid in self.indices['element'].get(element.lower(), set())]

    def process_relationships(self, entity_id: str, entity_data: Dict[str, Any]):
        """Process and create relationships for an entity."""
        try:
            # Element relationships
            if 'element' in entity_data.get('attributes', {}):
                element_name = entity_data['attributes']['element']
                element_id = self.resolve_or_create_element(element_name)
                if element_id:
                    self.add_relationship(entity_id, element_id, 'has_element')
            
            # Evolution relationships
            if 'evolves_from' in entity_data.get('attributes', {}):
                source_name = entity_data['attributes']['evolves_from']
                source_id = self.resolve_or_create_entity(source_name, 'monster')
                if source_id:
                    self.add_relationship(entity_id, source_id, 'evolves_from')
            
            # Faction relationships
            if 'faction' in entity_data.get('attributes', {}):
                faction_name = entity_data['attributes']['faction']
                faction_id = self.resolve_or_create_entity(faction_name, 'faction')
                if faction_id:
                    self.add_relationship(entity_id, faction_id, 'member_of')
            
            # Location relationships
            if 'location' in entity_data.get('attributes', {}):
                location_name = entity_data['attributes']['location']
                location_id = self.resolve_or_create_entity(location_name, 'location')
                if location_id:
                    self.add_relationship(entity_id, location_id, 'lives_in')
                
            # Process description for additional relationships
            if 'description' in entity_data.get('attributes', {}):
                self._extract_relationships_from_description(
                    entity_id, 
                    entity_data['attributes']['description']
                )
            
        except Exception as e:
            logger.error(f"Error processing relationships for entity {entity_id}: {str(e)}")

    def resolve_or_create_element(self, element_name: str) -> Optional[str]:
        """Resolve or create an element entity."""
        if not element_name:
            return None
        
        element_name = element_name.lower()
        
        # Check if element exists
        for eid, entity in self.entities.items():
            if (entity['entity_type'] == 'element' and 
                entity['name'].lower() == element_name):
                return eid
            
        # Create new element if it's a core element
        if element_name in self.core_elements:
            return self.add_entity(
                name=element_name.capitalize(),
                entity_type='element',
                attributes={
                    'symbol': self._get_element_symbol(element_name),
                    'is_core_element': True
                }
            )
        
        return None

    def resolve_or_create_entity(self, name: str, entity_type: str) -> Optional[str]:
        """Resolve or create an entity of given type."""
        if not name:
            return None
        
        name = name.strip()
        
        # Check if entity exists
        existing = self.get_entity_by_name(name)
        if existing and existing['entity_type'] == entity_type:
            return existing['id']
        
        # Create new entity
        return self.add_entity(
            name=name,
            entity_type=entity_type,
            attributes={'auto_created': True},
            metadata={'needs_verification': True}
        )

    def _extract_relationships_from_description(self, entity_id: str, description: str):
        """Extract relationships from entity description with enhanced patterns."""
        patterns = {
            'lives_in': [
                r'found in (the )?([\w\s]+)',
                r'lives in (the )?([\w\s]+)',
                r'inhabits (the )?([\w\s]+)',
                r'native to (the )?([\w\s]+)',
                r'located in (the )?([\w\s]+)'
            ],
            'evolves_from': [
                r'evolves from (the )?([\w\s]+)',
                r'evolved form of (the )?([\w\s]+)',
                r'evolution of (the )?([\w\s]+)',
                r'transforms from (the )?([\w\s]+)'
            ],
            'member_of': [
                r'member of (the )?([\w\s]+)',
                r'belongs to (the )?([\w\s]+)',
                r'part of (the )?([\w\s]+)',
                r'affiliated with (the )?([\w\s]+)'
            ],
            'allied_with': [
                r'allied with (the )?([\w\s]+)',
                r'allies of (the )?([\w\s]+)',
                r'aligned with (the )?([\w\s]+)'
            ],
            'hostile_to': [
                r'hostile to (the )?([\w\s]+)',
                r'enemies of (the )?([\w\s]+)',
                r'opposes (the )?([\w\s]+)',
                r'fights against (the )?([\w\s]+)'
            ],
            'controls': [
                r'controls (the )?([\w\s]+)',
                r'rules over (the )?([\w\s]+)',
                r'governs (the )?([\w\s]+)'
            ],
            'trades_with': [
                r'trades with (the )?([\w\s]+)',
                r'trading partner of (the )?([\w\s]+)',
                r'commerce with (the )?([\w\s]+)'
            ]
        }
        
        # Process each pattern
        for rel_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, description, re.IGNORECASE)
                for match in matches:
                    target_name = match.group(2).strip()
                    if target_name:
                        # Determine target entity type based on relationship
                        target_type = {
                            'lives_in': 'location',
                            'evolves_from': 'monster',
                            'member_of': 'faction',
                            'allied_with': 'faction',
                            'hostile_to': 'faction',
                            'controls': 'location',
                            'trades_with': 'faction'
                        }.get(rel_type)
                        
                        if target_type:
                            target_id = self.resolve_or_create_entity(target_name, target_type)
                            if target_id:
                                self.add_relationship(entity_id, target_id, rel_type) 