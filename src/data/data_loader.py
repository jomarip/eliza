import pandas as pd
from typing import List, Dict, Any, Optional
import os
from ..models.lore_entity import LoreEntity
import logging
import glob
from collections import defaultdict
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml
import json

logger = logging.getLogger(__name__)

# Define supported extensions and their handlers
SUPPORTED_EXTENSIONS = {
    'csv': 'CSVHandler',
    'json': 'JSONHandler',
    'txt': 'TextHandler',
    'md': 'MarkdownHandler',
    'yaml': 'YAMLHandler',
    'yml': 'YAMLHandler',
    'xml': 'XMLHandler'
}

class DataLoader:
    """Handles loading and processing of Hatchyverse data files."""
    
    # Filename pattern detection
    FILENAME_PATTERNS = {
        'generation': r'(gen(?:eration)?[\s\-_]*(\d+))',
        'type': r'(monster|item|story|world)',
        'category': r'(fire|water|earth|air|void|abyssal)'
    }
    
    # Column name mappings for different file formats
    MONSTER_COLUMNS = {
        'name': ['Name', 'name', 'monster_name'],
        'element': ['Element', 'element', 'type'],
        'description': ['Description', 'description', 'desc'],
        'id': ['Monster ID', 'id', 'monster_id'],
        'height': ['Height', 'height'],
        'weight': ['Weight', 'weight'],
        'generation': ['Generation', 'gen', 'version']
    }
    
    ITEM_COLUMNS = {
        'name': ['Name', 'name', 'item_name'],
        'type': ['Type', 'type', 'category'],
        'description': ['Description', 'description', 'desc'],
        'id': ['ID name', 'id', 'item_id'],
        'rarity': ['Rarity', 'rarity', 'grade']
    }
    
    def __init__(self, lore_base: str = "data"):
        """Initialize the DataLoader with a data directory."""
        self.lore_base = Path(lore_base)
        self.sources = {
            "official": self.lore_base/"official_canon",
            "community": self.lore_base/"community_vetted",
            "fan": self.lore_base/"fan_submissions"
        }
        
        # Create directories if they don't exist
        for path in self.sources.values():
            path.mkdir(parents=True, exist_ok=True)
        
        # Validate directory structure
        for name, path in self.sources.items():
            if not path.exists():
                logger.warning(f"Missing lore source directory: {name} ({path})")
        
        self.monster_data = {}
        self.item_data = {}
        self.story_data = {}
        self.world_data = {}
        
        # Initialize handlers
        self.handlers = {
            'csv': self._load_csv_data,
            'json': self._load_json_data,
            'txt': self._load_text_data,
            'md': self._load_text_data,
            'yaml': self._load_yaml_data,
            'yml': self._load_yaml_data,
            'xml': self._load_xml_data
        }
        
    def _extract_filename_metadata(self, filename: str) -> dict:
        """Extract metadata patterns from filenames."""
        metadata = {}
        
        # Generation detection with multiple patterns
        gen_match = re.search(
            self.FILENAME_PATTERNS['generation'], 
            filename, 
            re.IGNORECASE
        )
        if gen_match:
            metadata['generation'] = gen_match.group(2)
            metadata['generation_source'] = 'filename'
            
        # Cross-file relationships
        if 'gen' in filename.lower():
            metadata['is_generation_file'] = True
            metadata['file_group'] = 'primary'
        elif 'supplement' in filename.lower():
            metadata['file_group'] = 'supplemental'
            
        # Type detection
        type_match = re.search(
            self.FILENAME_PATTERNS['type'],
            filename,
            re.IGNORECASE
        )
        if type_match:
            metadata['content_type'] = type_match.group(1).lower()
            
        # Category/element detection
        category_match = re.search(
            self.FILENAME_PATTERNS['category'],
            filename,
            re.IGNORECASE
        )
        if category_match:
            metadata['category'] = category_match.group(1).lower()
            
        return metadata
        
    def _get_column_value(self, row: pd.Series, column_mappings: List[str], default: str = '') -> str:
        """Helper to get column value using multiple possible names."""
        for col in column_mappings:
            if col in row and pd.notna(row[col]):
                return str(row[col])
        return default
        
    def _validate_dataframe(self, df: pd.DataFrame, required_columns: List[str], source: str) -> bool:
        """Validate that DataFrame has required columns."""
        missing_columns = []
        for col_group in required_columns:
            if not any(col in df.columns for col in self.MONSTER_COLUMNS.get(col_group, [])):
                missing_columns.append(col_group)
        
        if missing_columns:
            logger.warning(f"Missing required columns in {source}: {missing_columns}")
            return False
        return True
        
    def _process_monsters(self, df: pd.DataFrame, source: str) -> List[LoreEntity]:
        """Process monster data with enhanced generation tracking."""
        entities = []
        
        # Extract metadata from filename
        filename_meta = self._extract_filename_metadata(os.path.basename(source))
        default_gen = filename_meta.get('generation', '1')
        
        for _, row in df.iterrows():
            try:
                # Get generation from row or filename metadata
                gen = str(row.get(self._map_column('generation', row)) or default_gen)
                
                # Create entity with enhanced metadata
                entity = LoreEntity(
                    id=f"{gen}_{row[self._map_column('id', row)]}",
                    name=row[self._map_column('name', row)],
                    entity_type="Hatchy",
                    element=row[self._map_column('element', row)].lower(),
                    description=row[self._map_column('description', row)],
                    metadata={
                        'generation': gen,
                        'generation_source': filename_meta.get('generation_source', 'data'),
                        'source': source,
                        'file_group': filename_meta.get('file_group', 'primary'),
                        'height': self._get_column_value(row, self.MONSTER_COLUMNS['height']),
                        'weight': self._get_column_value(row, self.MONSTER_COLUMNS['weight'])
                    },
                    sources=[source]
                )
                
                # Add cross-file relationships if this is a supplemental file
                if filename_meta.get('file_group') == 'supplemental':
                    entity.add_relationship(
                        target_id=f"gen_{gen}",
                        rel_type="supplements_generation",
                        strength=0.9
                    )
                
                entities.append(entity)
                logger.debug(f"Processed Hatchy: {entity.name} (Gen {gen})")
                
            except Exception as e:
                logger.error(f"Error processing monster row: {str(e)}")
                continue
                
        return entities
        
    def _process_items(self, df: pd.DataFrame, source: str) -> List[LoreEntity]:
        """Process item DataFrame into LoreEntity objects."""
        if df.empty:
            logger.warning(f"Empty item DataFrame from {source}")
            return []
            
        entities = []
        logger.debug(f"Processing {len(df)} items from {source}")
        logger.debug(f"Columns in {source}: {df.columns.tolist()}")
        
        if not self._validate_dataframe(df, ['name'], source):
            return []
            
        for idx, row in df.iterrows():
            try:
                name = self._get_column_value(row, self.ITEM_COLUMNS['name'])
                if not name:
                    logger.debug(f"Skipping item row {idx} without name in {source}")
                    continue
                    
                item_id = self._get_column_value(row, self.ITEM_COLUMNS['id'], f"item_{idx}")
                item_type = self._get_column_value(row, self.ITEM_COLUMNS['type'], 'Unknown')
                description = self._get_column_value(row, self.ITEM_COLUMNS['description'], f"A {item_type} item")
                
                metadata = {
                    'type': item_type,
                    'rarity': self._get_column_value(row, self.ITEM_COLUMNS['rarity'], 'common'),
                    'source': source
                }
                
                # Add any additional metadata columns
                for col in df.columns:
                    if not any(col in mapping for mapping in self.ITEM_COLUMNS.values()):
                        if pd.notna(row[col]):
                            metadata[col.lower()] = str(row[col])
                
                entity = LoreEntity(
                    id=item_id,
                    name=name,
                    entity_type="Item",
                    description=description,
                    metadata=metadata,
                    sources=[source]
                )
                entities.append(entity)
                logger.debug(f"Added item: {name} ({item_id})")
            except Exception as e:
                logger.error(f"Error processing item in {source} row {idx}: {str(e)}", exc_info=True)
                continue
        
        return entities
        
    def _load_monster_data(self):
        """Load monster data from CSV files."""
        monster_file_patterns = [
            "Hatchy - Monster Data - gen *.csv",
            "Hatchy Production Economy - Monster Data.csv"
        ]
        
        logger.debug(f"Searching for monster data files with patterns: {monster_file_patterns}")
        for pattern in monster_file_patterns:
            pattern_path = os.path.join(self.sources["official"], pattern)
            logger.debug(f"Searching with pattern: {pattern_path}")
            files = glob.glob(pattern_path)  # Removed recursive=True as files are in root
            logger.debug(f"Found {len(files)} files matching pattern '{pattern}': {files}")
            for file_path in files:
                try:
                    df = pd.read_csv(file_path)
                    filename = os.path.basename(file_path)
                    self.monster_data[filename] = df
                    logger.info(f"Loaded monster data from {filename} with {len(df)} rows")
                    logger.debug(f"Columns in {filename}: {list(df.columns)}")
                except Exception as e:
                    logger.error(f"Error loading monster data from {file_path}: {str(e)}", exc_info=True)
                    
    def _load_item_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load item-specific data."""
        try:
            df = pd.read_csv(file_path)
            items = []
            for _, row in df.iterrows():
                item = {
                    'name': row['Name'],
                    'type': row['Type'],
                    'description': row['Description'],
                    'attributes': {
                        'rarity': row.get('Rarity', 'common'),
                        'level': row.get('Level', 1)
                    }
                }
                items.append(item)
            return items
        except Exception as e:
            logger.error(f"Error loading item data from {file_path}: {str(e)}")
            return []
        
    def _load_story_data(self):
        """Load story data from text files."""
        story_file_patterns = [
            "Hatchy World Comic_ Chaos saga.txt"
        ]
        
        logger.debug(f"Searching for story data files with patterns: {story_file_patterns}")
        for pattern in story_file_patterns:
            pattern_path = os.path.join(self.sources["official"], pattern)
            logger.debug(f"Searching with pattern: {pattern_path}")
            files = glob.glob(pattern_path)  # Removed recursive=True as files are in root
            logger.debug(f"Found {len(files)} files matching pattern '{pattern}': {files}")
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    filename = os.path.basename(file_path)
                    self.story_data[filename] = {
                        'segments': self._parse_story_content(content)
                    }
                    logger.info(f"Loaded story data from {filename}")
                except Exception as e:
                    logger.error(f"Error loading story data from {file_path}: {str(e)}", exc_info=True)
                
    def _load_world_data(self):
        """Load world design data from text files."""
        world_file_patterns = [
            "Hatchy World _ world design.txt",
            "Hatchyverse Eco Presentation*.txt"
        ]
        
        logger.debug(f"Searching for world data files with patterns: {world_file_patterns}")
        for pattern in world_file_patterns:
            pattern_path = os.path.join(self.sources["official"], pattern)
            logger.debug(f"Searching with pattern: {pattern_path}")
            files = glob.glob(pattern_path)  # Removed recursive=True as files are in root
            logger.debug(f"Found {len(files)} files matching pattern '{pattern}': {files}")
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    filename = os.path.basename(file_path)
                    parsed_content = self._parse_world_content(content)
                    logger.debug(f"Parsed world content: {len(parsed_content.get('elements', {}))} elements, "
                               f"{len(parsed_content.get('regions', {}))} regions, "
                               f"{len(parsed_content.get('landmarks', []))} landmarks, "
                               f"{len(parsed_content.get('lore', []))} lore entries")
                    self.world_data[filename] = parsed_content
                    logger.info(f"Loaded world design data from {filename}")
                except Exception as e:
                    logger.error(f"Error loading world data from {file_path}: {str(e)}", exc_info=True)
                    
    def _parse_story_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse story content into segments with enhanced semantic understanding."""
        segments = []
        current_segment = None
        
        # Enhanced keywords for better concept detection
        concept_keywords = {
            'evolution': ['evolve', 'evolution', 'transform', 'stage', 'form'],
            'ability': ['ability', 'power', 'skill', 'attack', 'technique'],
            'location': ['found in', 'located', 'habitat', 'region', 'area', 'omniterra', 'felkyn'],  # Added specific locations
            'relationship': ['friend', 'enemy', 'ally', 'companion', 'rival', 'mentor'],
            'mechanics': ['ride', 'mount', 'equip', 'use', 'activate', 'summon'],
            'rarity': ['rare', 'legendary', 'mythical', 'unique', 'special', 'ancient'],
            'world': ['world', 'omniterra', 'continent', 'realm', 'dimension', 'felkyn', 'chaos'],  # Enhanced world concepts
            'lore': ['prophecy', 'legend', 'myth', 'history', 'tale', 'saga']  # Added lore concepts
        }
        
        # Enhanced section detection
        section_markers = {
            'chapter': r'Chapter\s+\d+|Episode\s+\d+',
            'arc': r'Arc\s*\d*:.*|Saga:.*',
            'scene': r'Scene\s*\d*:.*|\*\*\*|\-{3,}',
            'location': r'Location:.*|Setting:.*',
            'character': r'Character:.*|Cast:.*'
        }
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Check for section markers
            is_section_start = False
            section_type = None
            for marker_type, pattern in section_markers.items():
                if re.match(pattern, line, re.IGNORECASE):
                    is_section_start = True
                    section_type = marker_type
                    break
            
            if is_section_start or line.startswith('#') or line.isupper():
                if current_segment:
                    self._enrich_segment_metadata(current_segment, concept_keywords)
                    segments.append(current_segment)
                
                current_segment = {
                    'title': line.lstrip('#').strip(),
                    'content': '',
                    'characters': [],
                    'locations': [],
                    'concepts': defaultdict(list),
                    'context_tags': set(),
                    'world_concepts': [],
                    'section_type': section_type or 'general'
                }
            elif current_segment:
                current_segment['content'] += line + '\n'
                
                # Enhanced annotation extraction
                if '*' in line:
                    parts = line.split('*')
                    for part in parts[1:]:
                        part = part.strip()
                        if 'Character:' in part:
                            char_name = part.replace('Character:', '').strip()
                            current_segment['characters'].append({
                                'name': char_name,
                                'context': line
                            })
                        elif 'Location:' in part:
                            loc_name = part.replace('Location:', '').strip()
                            current_segment['locations'].append({
                                'name': loc_name,
                                'context': line
                            })
                
                # Enhanced world concept detection
                for concept_type, keywords in concept_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in line.lower():
                            # Get surrounding context
                            context_start = max(0, i - 2)
                            context_end = min(len(lines), i + 3)
                            context = '\n'.join(lines[context_start:context_end])
                            
                            if concept_type == 'world':
                                current_segment['world_concepts'].append({
                                    'concept': keyword,
                                    'context': context
                                })
                            current_segment['concepts'][concept_type].append({
                                'keyword': keyword,
                                'context': context
                            })
                            current_segment['context_tags'].add(concept_type)
            
            i += 1
        
        # Process the last segment
        if current_segment:
            self._enrich_segment_metadata(current_segment, concept_keywords)
            segments.append(current_segment)
        
        return segments
        
    def _enrich_segment_metadata(self, segment: Dict[str, Any], concept_keywords: Dict[str, List[str]]):
        """Enrich segment with metadata and cross-references."""
        content_lower = segment['content'].lower()
        
        # Extract character relationships
        for char in segment['characters']:
            char_name = char['name'].lower()
            for rel_type in ['friend', 'enemy', 'ally', 'rival', 'mentor']:
                if rel_type in content_lower:
                    # Find sentences containing both character and relationship
                    sentences = segment['content'].split('.')
                    for sentence in sentences:
                        if char_name in sentence.lower() and rel_type in sentence.lower():
                            if 'relationships' not in char:
                                char['relationships'] = []
                            char['relationships'].append({
                                'type': rel_type,
                                'context': sentence.strip()
                            })
        
        # Extract location details
        for loc in segment['locations']:
            loc_name = loc['name'].lower()
            # Find descriptive sentences about the location
            sentences = segment['content'].split('.')
            for sentence in sentences:
                if loc_name in sentence.lower():
                    if 'descriptions' not in loc:
                        loc['descriptions'] = []
                    loc['descriptions'].append(sentence.strip())
        
        # Add thematic tags
        segment['themes'] = []
        theme_patterns = {
            'conflict': ['battle', 'fight', 'struggle', 'conflict'],
            'friendship': ['friend', 'together', 'bond', 'trust'],
            'growth': ['learn', 'grow', 'change', 'develop'],
            'destiny': ['fate', 'destiny', 'prophecy', 'chosen'],
            'power': ['strength', 'power', 'ability', 'force']
        }
        
        for theme, patterns in theme_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                segment['themes'].append(theme)
                segment['context_tags'].add(f'theme_{theme}')
        
        # Convert tags to list for JSON serialization
        segment['context_tags'] = list(segment['context_tags'])
        
    def _parse_world_content(self, content: str) -> Dict[str, Any]:
        """Parse world design content."""
        world_data = {
            'elements': {},
            'regions': {},
            'landmarks': [],
            'lore': [],
            'world_concepts': [],  # Added to store high-level world concepts
            'locations': []  # Added to store major locations
        }
        
        current_section = None
        current_data = {}
        
        # Keywords for world concepts
        world_keywords = ['world', 'omniterra', 'continent', 'realm', 'dimension']
        
        # First pass - extract high-level world concepts
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Look for world-level concepts - more flexible matching
            if any(keyword in line.lower() for keyword in world_keywords):
                concept = {
                    'name': line.split(':')[0] if ':' in line else line,
                    'description': '',
                    'type': 'world_concept'
                }
                
                # Gather description from following lines
                j = i + 1
                while j < len(lines) and lines[j].strip() and not any(lines[j].strip().endswith(c) for c in [':', '*']):
                    concept['description'] += lines[j].strip() + ' '
                    j += 1
                
                world_data['world_concepts'].append(concept)
                i = j  # Skip the lines we've processed
            else:
                # Handle section headers
                if line.endswith(':'):
                    if current_section and current_data:
                        if current_section == 'Element':
                            world_data['elements'][current_data['name']] = current_data
                        elif current_section == 'Region':
                            world_data['regions'][current_data['name']] = current_data
                    
                    current_section = line[:-1].strip()
                    current_data = {'name': current_section}
                    
                # Handle region content
                elif line.startswith('-'):
                    if current_section == 'Region':
                        if 'locations' not in current_data:
                            current_data['locations'] = []
                        if 'landmarks' not in current_data:
                            current_data['landmarks'] = []
                            
                        location = line[1:].strip()
                        if any(keyword in location.lower() for keyword in 
                            ['temple', 'fortress', 'cave', 'palace', 'tower', 'shrine']):
                            current_data['landmarks'].append(location)
                            world_data['landmarks'].append(location)
                        else:
                            current_data['locations'].append(location)
                            world_data['locations'].append(location)
                            
                # Handle key-value pairs
                elif ':' in line:
                    key, value = line.split(':', 1)
                    current_data[key.strip().lower()] = value.strip()
                
                # Handle lore content
                elif line.startswith('THEMES') or line.startswith('ABOUT'):
                    world_data['lore'].append(line)
                
                i += 1
                
        # Add final section
        if current_section and current_data:
            if current_section == 'Element':
                world_data['elements'][current_data['name']] = current_data
            elif current_section == 'Region':
                world_data['regions'][current_data['name']] = current_data
                
        return world_data

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize dataframe values."""
        # Convert to string and strip whitespace for text columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()
        
        # Convert empty strings and 'nan' to None
        df = df.replace(r'^\s*$', None, regex=True)
        df = df.replace('nan', None)
        
        return df
    
    def load_all_data(self) -> List[Dict[str, Any]]:
        """Load all data from all sources."""
        all_entities = []
        
        for source_name, source_path in self.sources.items():
            if not source_path.exists():
                logger.debug(f"Source path does not exist: {source_path}")
                continue
            
            logger.debug(f"Loading data from source: {source_name} ({source_path})")
            for file_path in source_path.glob('**/*'):
                if not file_path.is_file():
                    continue
                
                ext = file_path.suffix.lower()[1:]  # Remove the dot
                logger.debug(f"Found file: {file_path} with extension {ext}")
                
                if ext not in self.handlers:
                    logger.debug(f"No handler for extension: {ext}")
                    continue
                
                try:
                    logger.debug(f"Processing file: {file_path}")
                    entities = self.handlers[ext](str(file_path))
                    if entities:
                        logger.debug(f"Loaded {len(entities)} entities from {file_path}")
                        all_entities.extend(entities)
                    else:
                        logger.debug(f"No entities loaded from {file_path}")
                
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {str(e)}")
        
        logger.info(f"Loaded total of {len(all_entities)} entities")
        return all_entities

    def _process_text_content(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Process text content to extract entity mentions and relationships."""
        fragments = []
        
        # Split into manageable chunks
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            # Extract entity mentions
            entity_mentions = self._extract_entity_mentions(para)
            
            if entity_mentions:
                fragments.append({
                    'text': para,
                    'source': source,
                    'mentions': entity_mentions,
                    'context_type': self._determine_context_type(para)
                })
        
        return fragments
    
    def _extract_entity_mentions(self, text: str) -> List[Dict[str, str]]:
        """Extract mentions of known entities from text."""
        mentions = []
        
        # Check for known entities
        for entity in self.all_entities.values():
            if entity.name.lower() in text.lower():
                context = self._extract_context(text, entity.name)
                mentions.append({
                    'entity_id': entity.id,
                    'name': entity.name,
                    'context': context
                })
        
        return mentions
    
    def _determine_context_type(self, text: str) -> str:
        """Determine the type of context for a text fragment."""
        context_indicators = {
            'evolution': ['evolve', 'evolution', 'transform'],
            'ability': ['ability', 'power', 'skill'],
            'location': ['found in', 'located', 'habitat'],
            'relationship': ['friend', 'enemy', 'ally'],
            'lore': ['legend', 'story', 'myth']
        }
        
        for context_type, indicators in context_indicators.items():
            if any(indicator in text.lower() for indicator in indicators):
                return context_type
        
        return 'general'
    
    def _extract_context(self, text: str, entity_name: str) -> str:
        """Extract relevant context around an entity mention."""
        # Find the sentence containing the entity
        sentences = text.split('.')
        for sentence in sentences:
            if entity_name.lower() in sentence.lower():
                return sentence.strip()
        return ""
    
    def _link_entities(self):
        """Create relationships between entities based on mentions."""
        for entity in self.all_entities.values():
            for fragment in entity.source_fragments:
                for mention in fragment.get('mentions', []):
                    if mention['entity_id'] in self.all_entities:
                        target_entity = self.all_entities[mention['entity_id']]
                        
                        # Add cross-references
                        entity.add_reference(
                            target_id=target_entity.id,
                            relationship=fragment['context_type'],
                            context=mention['context'],
                            source=fragment['source']
                        )
                        
                        # Add reverse reference
                        target_entity.mentioned_in.append(entity.id)
                        
                        # Add context tags
                        both_entities = [entity, target_entity]
                        for e in both_entities:
                            e.add_context_tags([
                                fragment['context_type'],
                                f"related_{e.entity_type.lower()}"
                            ])

    def _load_csv_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and process CSV data with type detection."""
        try:
            df = pd.read_csv(file_path)
            
            # Extract metadata from filename
            metadata = self._extract_filename_metadata(str(file_path))
            content_type = metadata.get('content_type')
            
            # Route to specific loader based on content type
            if content_type == 'monster':
                return self._process_monster_data(df, file_path)
            elif content_type == 'item':
                return self._load_item_data(file_path)
            else:
                # Generic CSV processing
                records = []
                for _, row in df.iterrows():
                    record = {
                        col: row[col] for col in df.columns 
                        if pd.notna(row[col])
                    }
                    record['metadata'] = metadata
                    records.append(record)
                return records
                
        except Exception as e:
            logger.error(f"Error loading CSV file {file_path}: {str(e)}")
            return []

    def _process_monster_data(self, df: pd.DataFrame, source_file: str) -> List[Dict[str, Any]]:
        """Process monster-specific CSV data."""
        monsters = []
        
        # Extract generation from filename
        gen_match = re.search(r'gen[^0-9]*([0-9]+)', str(source_file), re.IGNORECASE)
        generation = int(gen_match.group(1)) if gen_match else None
        
        for _, row in df.iterrows():
            monster = {
                'name': self._get_column_value(row, self.MONSTER_COLUMNS['name']),
                'element': self._get_column_value(row, self.MONSTER_COLUMNS['element']),
                'description': self._get_column_value(row, self.MONSTER_COLUMNS['description']),
                'attributes': {
                    'height': self._get_column_value(row, self.MONSTER_COLUMNS['height']),
                    'weight': self._get_column_value(row, self.MONSTER_COLUMNS['weight']),
                    'generation': generation or self._get_column_value(row, self.MONSTER_COLUMNS['generation'])
                },
                'metadata': {
                    'source_file': source_file,
                    'generation': generation,
                    'content_type': 'monster'
                }
            }
            
            # Only add if we have a valid name
            if monster['name']:
                monsters.append(monster)
            
        return monsters

    def _load_json_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load data from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle both list and dict formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Extract metadata from filename
                metadata = self._extract_filename_metadata(str(file_path))
                data['metadata'] = metadata
                return [data]
            else:
                logger.warning(f"Unexpected JSON format in {file_path}")
                return []
                
        except Exception as e:
            logger.error(f"Error loading JSON file {file_path}: {str(e)}")
            return []

    def _load_text_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load data from text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract metadata from filename
            metadata = self._extract_filename_metadata(str(file_path))
            
            # Split into segments if it's a story file
            if metadata.get('content_type') == 'story':
                segments = self._parse_story_content(content)
                return [{
                    'type': 'story',
                    'segments': segments,
                    'metadata': metadata
                }]
            else:
                # Generic text processing
                return [{
                    'content': content,
                    'metadata': metadata
                }]
                
        except Exception as e:
            logger.error(f"Error loading text file {file_path}: {str(e)}")
            return []

    def _load_yaml_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load data from YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            # Handle both list and dict formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Extract metadata from filename
                metadata = self._extract_filename_metadata(str(file_path))
                data['metadata'] = metadata
                return [data]
            else:
                logger.warning(f"Unexpected YAML format in {file_path}")
                return []
                
        except Exception as e:
            logger.error(f"Error loading YAML file {file_path}: {str(e)}")
            return []

    def _load_xml_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load data from XML file."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Convert XML to dict format
            def xml_to_dict(elem):
                result = {}
                for child in elem:
                    if len(child) > 0:
                        result[child.tag] = xml_to_dict(child)
                    else:
                        result[child.tag] = child.text
                return result
                
            data = xml_to_dict(root)
            
            # Extract metadata from filename
            metadata = self._extract_filename_metadata(str(file_path))
            data['metadata'] = metadata
            
            return [data]
            
        except Exception as e:
            logger.error(f"Error loading XML file {file_path}: {str(e)}")
            return []

# Add to existing handlers
class XMLHandler:
    def process(self, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        return [self._parse_element(elem) for elem in root]
        
    def _parse_element(self, elem):
        return {child.tag: child.text for child in elem}

class YAMLHandler:
    def process(self, file_path):
        with open(file_path) as f:
            return yaml.safe_load(f)

# Update supported extensions
SUPPORTED_EXTENSIONS.update({
    'xml': XMLHandler(),
    'yaml': YAMLHandler(),
    'yml': YAMLHandler()
}) 