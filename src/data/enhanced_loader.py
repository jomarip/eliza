import re

class PoliticalConflictLoader:
    def process_conflicts(self, text):
        conflicts = super().extract_relationships(text)
        
        # Add political relationship detection
        political_patterns = {
            'trade_dispute': r'trade dispute(?: between| with) (\w+) and (\w+)',
            'alliance_shift': r'(?:former|ex) allies (\w+) and (\w+)',
            'leadership_change': r'new leadership in (\w+) (?:affects|impacts)'
        }
        
        for rel_type, pattern in political_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                factions = match.groups()
                self.knowledge_graph.add_relationship(
                    factions[0], 
                    factions[1] if len(factions) > 1 else None,
                    rel_type,
                    context=text[match.start():match.end()]
                ) 