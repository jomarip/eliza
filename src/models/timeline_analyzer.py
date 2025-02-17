from typing import Dict, List, Any, Optional
from .knowledge_graph import HatchyKnowledgeGraph
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TimelineAnalyzer:
    """Analyzes temporal relationships and events in the knowledge graph."""
    
    def __init__(self, knowledge_graph: HatchyKnowledgeGraph):
        self.graph = knowledge_graph
        
    def get_events(self, timespan: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Get events within the specified timespan."""
        try:
            # Get all events from graph
            events = self.graph.get_entities_by_type('event')
            
            if not timespan:
                return events
                
            # Parse timespan
            try:
                start_date = datetime.fromisoformat(timespan['start'])
                end_date = datetime.fromisoformat(timespan['end'])
            except (ValueError, KeyError) as e:
                logger.error(f"Invalid timespan format: {e}")
                return []
                
            # Filter events by timespan
            filtered_events = []
            for event in events:
                event_date = event.get('attributes', {}).get('date')
                if event_date:
                    try:
                        event_datetime = datetime.fromisoformat(event_date)
                        if start_date <= event_datetime <= end_date:
                            filtered_events.append(event)
                    except ValueError as e:
                        logger.warning(f"Invalid date format for event {event['id']}: {e}")
                        continue
                        
            return filtered_events
            
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return [] 