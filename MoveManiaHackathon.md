# MoveMania Hackathon: Hatchyverse Lore System Implementation Plan

## Project Codename: LoreForge

### Core Objectives
1. **Dynamic Lore Engine** - AI-mediated community contributions with auto-validation
2. **Canon Consistency** - Multi-layer conflict detection system
3. **Decentralized Governance** - Community voting on contested lore elements
4. **Contributor Economy** - Token incentives for quality contributions (HatchyTokens)

## Phase 1: Core Infrastructure 

### 1.1 Enhanced Lore Agent (Urban Griotz)
**Implementation Files:**
- `characters/lorekeeper_eliza.json` (New character config)
- `src/models/enhanced_chatbot.py` (Existing core)

**Key Features:**
```python
# Sample personality traits
personality = {
    "archetype": "Wise Archivist",
    "traits": ["Historically Precise", "Community Focused", "Canon Guardian"],
    "communication_style": {
        "base": "Socratic questioning",
        "error_handling": "Constructive myth-building"
    }
}
```

### 1.2 Knowledge Graph Integration
**Implementation Files:**
- `src/models/knowledge_graph.py` (Existing)
- `src/data/enhanced_loader.py` (Existing)

**Augmentation Strategy:**
example:
```python
class PoliticalConflictLoader:
    """Specialized loader for faction relationships"""
    def process_conflicts(self, text):
        # Use existing relationship extraction patterns
        conflicts = self.relationship_extractor.extract(text)
        # Add political-specific relationship types
        self._add_political_relationships(conflicts)
```

### 1.3 Semantic Search Backbone
**Implementation Plan:**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

# Using existing infrastructure from src/models/contextual_retriever.py
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", "(?<=\. )"]
)

embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-base-en-v1.5",
    encode_kwargs={'normalize_embeddings': True}
)
```

## Phase 2: Community Integration 

### 2.1 Lore Submission System
**Implementation Files:**
- `src/api/main.py` (Extend existing FastAPI endpoints)
- `contracts/LoreSubmission.move` (New Aptos smart contract)

**Key Components:**
```move
module LoreSubmission {
    struct LoreProposal has key {
        content: String,
        submitter: address,
        votes: u64,
        status: u8,
        validation_hash: String
    }
    
    public entry fun submit_proposal(
        content: String,
        validation_hash: String
    ) {
        // Matches validation system in src/models/lore_validator.py
    }
}
```

### 2.2 Conflict Detection Engine
**Augmentation of Existing Systems:**
```python
# Building on src/models/lore_validator.py
class EnhancedConflictDetector(LoreValidator):
    def check_conflict(self, submission):
        # Existing vector store check
        base_result = super().check_conflict(submission)
        
        # New political consistency check
        political_conflicts = self._check_faction_consistency(submission)
        
        return {
            **base_result,
            "political_conflicts": political_conflicts,
            "total_severity": base_result["score"] + political_conflicts["score"]
        }
```

## Phase 3: Frontend & Accessibility 

### 3.1 Community Interface
**Implementation Strategy:**
```jsx
// Using existing component structure from eliza UI
<LoreDashboard>
  <ConflictVisualizer graphData={knowledgeGraph} />
  <SubmissionTimeline proposals={proposals} />
  <VotingInterface governanceContract={contract} />
</LoreDashboard>
```

### 3.2 Blockchain Integration
**Environment Setup:**
```python
# Augmenting existing .env.example configurations
APTOS_NODE_URL="https://fullnode.mainnet.aptoslabs.com"
HATCHY_TOKEN_CONTRACT="0x1234...5678"
SUBMISSION_FEE=0.5  # In HatchyTokens
```

## Phase 4: Testing & Deployment 

### 4.1 Testing Matrix
**Key Test Cases:**
1. World Knowledge Validation
   - Accurately describe Omniterra's regions and key locations
   - Identify major historical events and their impact
   - Map faction territories and sphere of influence

2. Generation & Evolution Data
   - List complete Gen1 Hatchy roster with types
   - Track evolution chains across generations
   - Compare attributes between related Hatchy (e.g. Firret vs Firadactus)
   - Identify mount-capable evolved forms

3. Character & Lore Details  
   - Provide detailed character profiles (e.g. Ixor background)
   - Map relationships between characters
   - Track item associations (e.g. Buzzkill armor pieces)

4. Cross-Reference Integrity
   - Validate evolution chain consistency
   - Check type matchups and balancing
   - Verify equipment and character relationships

5. Community Knowledge Integration
   - Process new lore submissions
   - Detect conflicts with existing canon
   - Resolve contradictory information

### 4.2 Deployment Strategy
```bash
# Using existing eliza deployment workflows
fleek deploy --include-aptos-modules --env political-lore
```

## Post-Hackathon Roadmap

1. **Lore Provenance System** - Track contribution history on-chain
2. **Dynamic Timeline Engine** - Auto-generate chronology from submissions
3. **Cross-IP Integration** - Allow licensed external IP contributions

## Team Structure

1. **Lore Architecture** - Knowledge graph & validation systems
2. **Community Engine** - Submission & governance interfaces
3. **Narrative Integrity** - Conflict detection & AI training
4. **Blockchain Integration** - Aptos contracts & token flows
