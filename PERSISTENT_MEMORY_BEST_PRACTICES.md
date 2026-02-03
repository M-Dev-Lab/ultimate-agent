# 🧠 Persistent Memory in AI Agents: Best Practices & Implementation Patterns

**Based on Production Research & Real Implementations**  
**Date**: February 2026  
**Focus**: Hallucination Reduction, Semantic Grounding, Rule Constraints, Memory Consolidation

---

## Table of Contents
1. [Core Architecture Patterns](#core-architecture-patterns)
2. [Multi-Tier Memory Systems](#multi-tier-memory-systems)
3. [Hallucination Prevention Through Fact-Grounding](#hallucination-prevention)
4. [Vector Databases & Semantic Search](#vector-databases--semantic-search)
5. [Rule & Constraint Systems](#rule--constraint-systems)
6. [Memory Consolidation & Reflection](#memory-consolidation--reflection)
7. [Prompt Engineering Techniques](#prompt-engineering-techniques)
8. [Implementation Patterns](#implementation-patterns)
9. [Production Examples](#production-examples)

---

## Core Architecture Patterns

### 1. **RAG (Retrieval-Augmented Generation)** ✅

**Why It Works for Hallucinations:**
- Grounds model responses in retrieved facts, not invented content
- Provides citations (file + line numbers) for traceability
- Reduces confidence in uncertain information

**Key Pattern:**
```
User Query → Semantic Search → Retrieve Top-K Facts → 
Enhance Prompt with Retrieved Context → Generate Response with Citations
```

**Implementation Approach** (from workspace):
- Use vector databases (Chroma, LanceDB) for embeddings
- Store code snippets, documentation, and conversation history
- Search before answering about: prior work, decisions, dates, people, preferences, todos
- Return top results with path + line numbers for verification

**Code Example** (from python-agent):
```python
async def search_documentation(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Search documentation for relevant information"""
    results = self.documentation_collection.query(
        query_texts=[query],
        n_results=n_results
    )
    formatted_results = []
    if results["ids"] and len(results["ids"]) > 0:
        for idx, doc_id in enumerate(results["ids"][0]):
            formatted_results.append({
                "id": doc_id,
                "content": results["documents"][0][idx],
                "distance": results["distances"][0][idx],
                "metadata": results["metadatas"][0][idx]
            })
    return formatted_results
```

### 2. **Experience Replay** 

**Concept:**
- Store successful agent interactions (trajectories) in a vector database
- Retrieve similar past solutions when facing new problems
- Learn from patterns in past reasoning chains

**Benefits:**
- Reduces exploration time (agent doesn't re-invent solutions)
- Provides worked examples for in-context learning
- Enables transfer learning across similar tasks

**Structure:**
```json
{
  "problem": "Add authentication to API",
  "solution_trajectory": [
    {"step": 1, "action": "search jwt patterns", "result": "..."},
    {"step": 2, "action": "implement middleware", "result": "..."},
    {"step": 3, "action": "test auth flow", "result": "..."}
  ],
  "success_score": 0.95,
  "timestamp": "2026-01-15"
}
```

### 3. **Episodic Memory** (Session-Based)

**Pattern:**
- Store complete conversation contexts with metadata
- Index by date, agent, participant, tags
- Retrieve for context within token budgets

**Use Cases:**
- Quick context loading for follow-up conversations
- Finding precedent interactions ("Have we discussed this before?")
- Building conversation continuity

**Implementation:**
```python
class ConversationCollection:
    """Store and retrieve complete conversation episodes"""
    async def store_episode(self, episode: EpisodeData):
        # Store full conversation with metadata
        self.collection.add(
            ids=[episode.id],
            documents=[episode.full_text],
            embeddings=[episode.vector],
            metadatas=[{
                "date": episode.date,
                "participants": episode.participants,
                "topic": episode.topic,
                "outcome": episode.outcome
            }]
        )
    
    async def retrieve_similar_episodes(self, query: str, limit: int = 3):
        # Find relevant past conversations
        vector = await self.embeddings.embed(query)
        return self.collection.query(
            query_embeddings=[vector],
            n_results=limit,
            where={"outcome": {"$eq": "successful"}}
        )
```

---

## Multi-Tier Memory Systems

### **Four-Layer Architecture** (Hindsight + Letta Pattern)

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: SHORT-TERM (Context Window)                       │
│  ├─ Current conversation                                    │
│  ├─ Immediate context (fast, ~10-100 tokens)               │
│  └─ Used for immediate reasoning                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: EPISODIC (Session-Based)                          │
│  ├─ Complete conversation history                           │
│  ├─ Decisions made in this session                          │
│  ├─ Tool calls and outcomes                                 │
│  └─ Retrieved via semantic search (~500-1500 tokens)        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: SEMANTIC (Vector-Indexed)                         │
│  ├─ Structured facts + observations                         │
│  ├─ Code patterns & best practices                          │
│  ├─ Entity-aware: @User, @Topic, @Pattern                  │
│  └─ Confidence scores: opinions evolve with evidence        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: RULES/CONSTRAINTS (Always In Context)            │
│  ├─ System rules (MUST, MUST NOT, SHOULD)                  │
│  ├─ User preferences (hard constraints)                     │
│  ├─ Agent guidelines (behavior boundaries)                  │
│  └─ Safety guardrails (non-negotiable, <500 tokens)        │
└─────────────────────────────────────────────────────────────┘
```

### **Practical Implementation: From Workspace**

```markdown
~/.openclaw/workspace/
├── MEMORY.md                      # Core facts (Layer 4 + Layer 3)
│   ├─ Durable facts & preferences
│   ├─ User identity & constraints
│   └─ Always loaded in main session
│
├── memory/YYYY-MM-DD.md           # Daily log (Layer 2 + Layer 3)
│   ├─ Append-only narrative
│   ├─ Decisions with rationale
│   ├─ Read today + yesterday at session start
│   └─ Vector-indexed for semantic search
│
├── bank/                          # Curated memory (Layer 3)
│   ├── world.md                   # Objective facts (grounded)
│   ├── experience.md              # Agent's work (first-person)
│   ├── opinions.md                # Subjective + confidence
│   └── entities/                  # @Person, @Topic pages
│
└── skills/                        # Persistent rules (Layer 4)
    └── [Agent-specific guidelines]
```

**Key Insight**: Rules stay small (always in context), episodic grows (selectively retrieved), semantic is indexed (fast lookup).

---

## Hallucination Prevention

### **1. Mandatory Recall Step in Prompts**

**Anti-Pattern** ❌ (causes hallucinations):
```
"Answer questions about prior work, decisions, and preferences."
```

**Better Pattern** ✅ (forces fact-grounding):
```
"## Memory Recall

Before answering anything about prior work, decisions, dates, 
people, preferences, or todos: 
1. Run memory_search on MEMORY.md + memory/*.md
2. Use memory_get to pull only the needed lines
3. If low confidence after search, say you checked.
4. Never invent dates, people, or decisions."
```

**Implementation**:
```typescript
function buildMemorySection(params: { isMinimal: boolean; availableTools: Set<string> }) {
  if (params.isMinimal || !params.availableTools.has("memory_search")) {
    return [];
  }
  return [
    "## Memory Recall",
    "Before answering anything about prior work, decisions, dates, people, preferences, or todos: run memory_search on MEMORY.md + memory/*.md; then use memory_get to pull only the needed lines. If low confidence after search, say you checked.",
    "",
  ];
}
```

### **2. Confidence-Bearing Opinions** (Hindsight Pattern)

**Structure**:
```markdown
## Retain (Extract Facts Daily)

- W (World) @Peter: Currently in Marrakech (Nov 27–Dec 1, 2025)
  - Weight: Objective fact (grounded in calendar)
  
- O (Opinion) @warelay: Prefers `git rebase` over merge
  - Confidence: c=0.8 (observed 4 times, never contradicted)
  - Evidence: [memory/2025-11-20.md], [memory/2025-11-15.md]

- B (Experience) @self: Fixed Baileys WS crash with try/catch
  - Confidence: c=0.95 (tested, documented)
  - File: memory/2025-11-27.md

- S (Summary): Need to review auth implementation
  - Confidence: c=0.6 (preliminary, needs validation)
```

**Algorithm for Opinion Evolution**:
```python
def update_confidence(opinion, new_evidence):
    """
    Evolve confidence based on repeated evidence or contradiction
    """
    if aligns_with_opinion(new_evidence):
        # Small positive delta
        confidence += 0.05 * (1 - confidence)  # Diminishing returns
    elif contradicts_opinion(new_evidence):
        # Larger negative delta (learn faster from contradictions)
        confidence -= 0.15
    
    # Bounds: [0, 1]
    return max(0, min(1, confidence))
```

### **3. Citation System**

**Pattern**:
```
Answer: "User prefers concise replies (<1500 chars)."
Citation: memory/2025-11-20.md:42-45
Confidence: 0.85 (observed 3x, consistent)
```

**Python Implementation** (Chroma):
```python
async def search_similar_code(self, query: str, n_results: int = 5, 
                             build_id: Optional[str] = None) -> List[Dict[str, Any]]:
    results = self.code_collection.query(
        query_texts=[query],
        n_results=n_results,
        where={"build_id": {"$eq": build_id}} if build_id else None
    )
    
    formatted_results = []
    if results["ids"] and len(results["ids"]) > 0:
        for idx, doc_id in enumerate(results["ids"][0]):
            formatted_results.append({
                "id": doc_id,
                "content": results["documents"][0][idx],
                "distance": results["distances"][0][idx],  # Score
                "metadata": results["metadatas"][0][idx],
                "source_file": results["metadatas"][0][idx].get("source_file"),
                "language": results["metadatas"][0][idx].get("language")
            })
    return formatted_results
```

---

## Vector Databases & Semantic Search

### **1. Collection Structure** (From Production Code)

```python
class VectorStore:
    """Chroma vector database wrapper for semantic search"""
    
    def _init_collections(self):
        """Initialize collection structure"""
        self.code_collection = self.client.get_or_create_collection(
            name="code_snippets",
            metadata={"description": "Indexed code snippets for RAG"}
        )
        
        self.documentation_collection = self.client.get_or_create_collection(
            name="documentation",
            metadata={"description": "Project documentation and API docs"}
        )
        
        self.conversation_collection = self.client.get_or_create_collection(
            name="conversations",
            metadata={"description": "Conversation history for context"}
        )
        
        self.best_practices_collection = self.client.get_or_create_collection(
            name="best_practices",
            metadata={"description": "Code patterns and best practices"}
        )
```

### **2. Hybrid Search: BM25 + Vector** (Optimal Pattern)

**Why Hybrid?**
- **BM25 (Full-Text)**: Exact keyword matches, technical terms
- **Vector**: Semantic similarity, paraphrases, context
- **Combined**: Best of both worlds

**Configuration** (OpenClaw):
```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "query": {
          "maxResults": 10,
          "minScore": 0.5,
          "hybrid": {
            "enabled": true,
            "vectorWeight": 0.6,
            "textWeight": 0.4,
            "candidateMultiplier": 4
          }
        }
      }
    }
  }
}
```

**Algorithm**:
```python
async def hybrid_search(query: str, limit: int = 10):
    # 1. BM25 full-text search
    bm25_results = await db.search_fts(query, k=limit * 4)
    bm25_scores = {r['id']: bm25_relevance(r) for r in bm25_results}
    
    # 2. Vector semantic search  
    vector = await embeddings.embed(query)
    vector_results = await db.search_vector(vector, k=limit * 4)
    vector_scores = {r['id']: r['distance'] for r in vector_results}
    
    # 3. Merge with weighted combination
    merged = {}
    for doc_id in set(bm25_scores.keys()) | set(vector_scores.keys()):
        bm25 = bm25_scores.get(doc_id, 0)
        vector = vector_scores.get(doc_id, 0)
        score = 0.4 * bm25 + 0.6 * vector
        merged[doc_id] = score
    
    # 4. Return top-k by combined score
    return sorted(merged.items(), key=lambda x: x[1], reverse=True)[:limit]
```

### **3. SQLite Vector Acceleration** (Performance Pattern)

**Setup**:
```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "store": {
          "driver": "sqlite",
          "path": "~/.openclaw/memory/{agentId}.sqlite",
          "vector": {
            "enabled": true,
            "extensionPath": "/path/to/sqlite-vec"
          }
        }
      }
    }
  }
}
```

**Benefits**:
- ✅ Sub-100ms vector distance queries
- ✅ No separate service (embedded)
- ✅ Persistent on-disk
- ✅ Full-text search (FTS5) + vectors combined

### **4. Embedding Model Selection**

| Model | Dimensions | Latency | Cost | Best For |
|-------|-----------|---------|------|----------|
| text-embedding-3-small | 1536 | 1ms | $ | Fast, default choice |
| text-embedding-3-large | 3072 | 2ms | $$ | Accuracy-critical |
| Local (Ollama) | 768-1024 | 10-50ms | FREE | Offline, privacy |
| Gemini | 768 | 2ms | $ | Multi-modal |

**Fallback Strategy**:
```python
def get_embedding_model(primary_provider="openai", fallback="local"):
    try:
        return OpenAIEmbeddings(model="text-embedding-3-small")
    except Exception as e:
        logger.warn(f"Primary embeddings failed: {e}")
        return OllamaEmbeddings(model="nomic-embed-text")  # Free fallback
```

---

## Rule & Constraint Systems

### **1. Persistent Rules (File-Based)**

**Structure** (always in context):
```markdown
# SOUL.md - Agent Identity & Boundaries

## Core Constraints

### MUST (Non-negotiable)
- MUST verify facts before citing them
- MUST cite sources with file paths
- MUST refuse unsafe code generation
- MUST ask permission before writing files

### MUST NOT (Prohibited)
- MUST NOT make up dates or people
- MUST NOT bypass auth systems
- MUST NOT delete production data
- MUST NOT run unreviewed code

### SHOULD (Guidance)
- SHOULD prefer explicit to implicit
- SHOULD explain reasoning
- SHOULD offer alternatives
- SHOULD suggest tests

## Tone & Personality
- Communicate clearly, concisely
- Be helpful without being pushy
- Admit uncertainty
- Ask clarifying questions
```

### **2. Constraint Injection Pattern**

**Before Agent Execution**:
```python
def build_system_prompt(workspace_dir: str) -> str:
    base = """You are a helpful AI assistant."""
    
    # Load persistent rules
    soul_md = read_file(f"{workspace_dir}/SOUL.md")
    identity_md = read_file(f"{workspace_dir}/IDENTITY.md")
    rules_md = read_file(f"{workspace_dir}/RULES.md")
    
    # Combine in priority order
    return f"""{base}

{soul_md}

{identity_md}

## Mandatory Rules
{rules_md}

## Safety Checklist
- [ ] Verified all facts before citing
- [ ] Included source citations
- [ ] Confirmed permissions before actions
- [ ] No invented information
"""
```

### **3. Constraint Checking (Post-Generation)**

**Algorithm**:
```python
async def validate_response(response: str, rules: Rules) -> ValidationResult:
    """Check response against constraints before delivery"""
    
    violations = []
    
    # Check MUST-NOTs (immediate rejection)
    for must_not in rules.must_nots:
        if violates(response, must_not):
            violations.append({"severity": "CRITICAL", "rule": must_not})
            return ValidationResult(success=False, violations=violations)
    
    # Check MUSTs (require remediation)
    for must in rules.musts:
        if not satisfies(response, must):
            violations.append({"severity": "HIGH", "rule": must})
    
    # Check SHOULDs (log warnings)
    for should in rules.shoulds:
        if not satisfies(response, should):
            violations.append({"severity": "LOW", "rule": should})
    
    return ValidationResult(
        success=len([v for v in violations if v["severity"]=="CRITICAL"]) == 0,
        violations=violations
    )
```

### **4. Dynamic Rule Updates**

**Pattern**:
```python
async def update_user_rules(user_id: str, rule_updates: Dict[str, Any]):
    """User can update their own constraints dynamically"""
    
    current_rules = await db.get_user_rules(user_id)
    
    # Validate updates don't violate system constraints
    for rule_key, rule_value in rule_updates.items():
        if violates_system_safety(rule_key, rule_value):
            raise PermissionError(f"Rule {rule_key} violates system safety")
    
    # Merge updates
    updated_rules = {**current_rules, **rule_updates}
    
    # Persist
    await db.set_user_rules(user_id, updated_rules)
    
    # Log for audit trail
    logger.info(f"Rules updated for user {user_id}", extra={"changes": rule_updates})
```

---

## Memory Consolidation & Reflection

### **1. Retain / Recall / Reflect Loop**

```
┌─ RETAIN ─────────────────────────────────┐
│ Extract narrative facts from daily log   │
│ Tag with: Type(W/B/O/S) + Entities      │
│ Store with confidence scores            │
│ File: memory/YYYY-MM-DD.md              │
└─────────────────────────────────────────┘
           ↓
┌─ RECALL ─────────────────────────────────┐
│ Query semantically similar facts        │
│ Rank by confidence + recency             │
│ Return with citations & evidence        │
│ Used by agent for context               │
└─────────────────────────────────────────┘
           ↓
┌─ REFLECT ────────────────────────────────┐
│ Scheduled job (daily/heartbeat)         │
│ Update bank/entities/*.md               │
│ Evolve opinion confidences              │
│ Propose edits to core facts             │
│ Output: bank/opinions.md (evolving)     │
└─────────────────────────────────────────┘
```

### **2. Retention Rules** (What to Extract)

```markdown
## Memory Capture Policy

### Capture These (High Value)
- Decisions with rationale
- User preferences (explicit mentions)
- Important events & dates
- Lessons learned
- Blocked issues & resolutions

### Skip These (Low Value)
- Generic greetings
- Repeated small talk
- Meta-comments ("I'm thinking...")
- Debugging noise
- Transient system info

### Example: Narrative Facts

❌ Bad (too granular):
```
- User said "hello"
- System responded "hi"
- User asked question
```

✅ Good (self-contained narrative):
```
- W @User: Prefers concise replies (<1500 chars) on messaging apps
- B @Team: Implemented JWT auth using RS256, validated with 10k req/sec load
- O @Project: Next.js better than alternatives for this use case (c=0.85)
- D @System: Chose PostgreSQL over MongoDB (reasoning: ACID compliance)
```
```

### **3. Memory Flush** (Compaction on Context Pressure)

**Trigger**:
```python
def should_run_memory_flush(session: Session) -> bool:
    """Check if token budget requires consolidation"""
    
    soft_threshold = 0.8 * context_window  # 80% full
    current_tokens = session.calculate_token_count()
    
    # Don't flush twice in same compaction cycle
    if session.memoryFlushAt == session.compactionCount:
        return False
    
    return current_tokens > soft_threshold
```

**Process** (from production code):
```python
async def run_memory_flush(session: Session) -> CompactionResult:
    """
    Compaction: Summarize and consolidate session memory
    1. Call LLM to extract key facts & decisions
    2. Update bank/ files with consolidated view
    3. Clear old messages from context
    4. Increment compaction counter
    """
    
    # Build consolidation prompt
    prompt = f"""
    Consolidate this session into key facts & decisions:
    
    --- Session Transcript ---
    {session.transcript}
    
    Output:
    - Key decisions made
    - Important facts learned
    - Lessons for future
    - Questions remaining
    """
    
    consolidation = await llm.generate(prompt)
    
    # Update persistent memory
    await update_memory_file("bank/experience.md", consolidation)
    
    # Clear old messages, keep compaction summary
    session.compact(keep_summary=True)
    
    return CompactionResult(
        tokens_saved=original_tokens - session.tokens,
        facts_extracted=len(consolidation.facts)
    )
```

---

## Prompt Engineering Techniques

### **1. Structure Prompts for Memory Leverage**

**Pattern: Memory-First Questions**
```markdown
## Before answering about [topic]:

1. **Memory Search**: What do we know about this?
   ```
   Run: memory_search("@User preferences AND @Topic")
   ```

2. **Check Constraints**: What are the rules?
   ```
   Load: SOUL.md, RULES.md for this domain
   ```

3. **Find Precedents**: Have we solved similar problems?
   ```
   Query: bank/experience.md for @Pattern matches
   ```

4. **Answer with Evidence**:
   - Cite source files
   - Include confidence scores
   - Explain reasoning chain
```

**Implementation**:
```typescript
function buildMemorySection(params) {
  return [
    "## Memory Recall",
    "Before answering anything about prior work, decisions, dates, people, preferences, or todos:",
    "1. Run memory_search on MEMORY.md + memory/*.md",
    "2. Use memory_get to pull only the needed lines",
    "3. Include source citations (file:linerange)",
    "4. Report confidence if uncertain",
    "5. If low confidence after search, say you checked.",
    "",
  ];
}
```

### **2. Few-Shot Examples with Citations**

**Pattern**:
```markdown
## Examples with Citations

### Example 1: User Preference
**Memory Recall Result**: 
- Source: memory/2025-11-20.md:42-45
- Fact: "User prefers concise replies (<1500 chars) for WhatsApp"
- Confidence: 0.85 (observed 3 times consistently)

**Your Response**:
"Based on your preference for brief messages, here's a concise explanation..."

### Example 2: Technical Decision
**Memory Recall Result**:
- Source: bank/experience.md:128-135
- Decision: "Chose PostgreSQL over MongoDB for ACID compliance"
- Confidence: 0.95 (documented, tested at scale)

**Your Response**:
"Following your decision criteria and past success with PostgreSQL, I recommend..."
```

### **3. Confidence Expression in Language**

```markdown
## Confidence-Grounded Language

| Confidence | Phrasing | Example |
|-----------|----------|---------|
| c=0.95+ | State as fact | "You prefer X" |
| c=0.75-0.94 | Likely/probably | "You likely prefer X" |
| c=0.50-0.74 | Possibly | "You may prefer X" |
| c=<0.50 | Uncertain | "I'm unsure about X" |
| Unknown | Ask | "Have you considered X?" |

## Anti-Patterns ❌
- "Based on my understanding..." (vague)
- "I assume you..." (uncertain)
- "It seems..." (non-committal)

## Better Patterns ✅
- "Memory shows: [fact] (confidence: 0.85)"
- "Your preference (from memory/2025-11-20.md): [fact]"
- "I checked memory and found no info on this. Should I...?"
```

### **4. Tool-Call Patterns for Memory Access**

**Mandatory Recall Before Claims**:
```markdown
User: "What's my preferred communication style?"

Agent Execution:
1. Tool: memory_search("@User communication preferences")
   Result: 
   - memory/2025-11-20.md: "Prefers concise, direct replies (<1500 chars)"
   - Confidence: 0.85
   - Source: 3 consistent observations

2. Tool: memory_get("memory/2025-11-20.md", lines="42-45")
   Result: Full context with surrounding decisions

3. Response:
   "Your preferred communication style:
   - Format: Concise, direct (<1500 chars)
   - Source: memory/2025-11-20.md:42-45
   - Confidence: 0.85 (consistent across 3 observations)
   
   Would you like me to adjust this preference?"
```

---

## Implementation Patterns

### **Pattern 1: RAG Context Injection**

```python
async def generate_response_with_rag(user_query: str, context: Context) -> str:
    """Standard RAG pattern for grounded generation"""
    
    # 1. Retrieve relevant facts
    memory_results = await context.vector_store.search(user_query, top_k=5)
    documentation = await context.vector_store.search_documentation(user_query, top_k=3)
    
    # 2. Format retrieved context
    rag_context = format_retrieval_context(memory_results, documentation)
    
    # 3. Build prompt with injected context
    prompt = f"""
    Answer the following question using the provided context.
    If information is not in the context, say so.
    Always cite sources.
    
    Context:
    {rag_context}
    
    Question: {user_query}
    
    Answer (include citations):
    """
    
    # 4. Generate with grounding
    response = await llm.generate(prompt)
    
    return response  # Contains citations from memory
```

### **Pattern 2: Multi-Layer Retrieval**

```python
async def multi_layer_retrieval(query: str) -> Dict[str, Any]:
    """Retrieve from all memory layers efficiently"""
    
    results = {
        "rules": await load_rules(),  # LAYER 4 - Always ready
        "semantic": await search_semantic(query, top_k=5),  # LAYER 3 - Vector indexed
        "episodic": await search_conversations(query, top_k=3),  # LAYER 2 - Conversation history
        "context": get_current_context()  # LAYER 1 - Already loaded
    }
    
    # Rank by relevance and combine
    combined = combine_results(results, strategy="relevance_then_recency")
    
    return {
        "grounded_facts": combined[:5],
        "confidence_scores": [r.confidence for r in combined],
        "source_citations": [r.source_file for r in combined]
    }
```

### **Pattern 3: Constraint Validation Pipeline**

```python
async def safe_generate_response(query: str, agent_rules: Rules) -> SafeResponse:
    """Generate with constraint checking"""
    
    # 1. Load persistent rules
    rules_context = format_rules(agent_rules)
    
    # 2. Generate with rules injected
    initial_response = await llm.generate(
        prompt=f"{rules_context}\n\nUser: {query}",
        temperature=0.3  # Lower temp for constraint adherence
    )
    
    # 3. Validate against constraints
    violations = await validate_response(initial_response, agent_rules)
    
    if violations.has_critical():
        # Regenerate with stronger constraint emphasis
        initial_response = await llm.generate(
            prompt=f"{rules_context}\n\nIMPORTANT: {format_violations(violations)}\n\nUser: {query}",
            temperature=0.1
        )
    
    # 4. Return with validation results
    return SafeResponse(
        content=initial_response,
        validated=True,
        violations=violations
    )
```

### **Pattern 4: Memory Refresh on Startup**

```python
async def initialize_session(session_key: str) -> Session:
    """Load memory at session start for grounding"""
    
    session = Session(key=session_key)
    
    # 1. Load MEMORY.md (core facts)
    session.core_memory = await load_file("MEMORY.md")
    
    # 2. Load today's memory + yesterday (context)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(1)).strftime("%Y-%m-%d")
    session.recent_memory = await load_memory_file(f"memory/{today}.md")
    session.recent_memory += await load_memory_file(f"memory/{yesterday}.md")
    
    # 3. Index for fast retrieval
    await session.vector_store.index_memory(session.recent_memory)
    
    # 4. Load SOUL.md (behavioral rules)
    session.soul = await load_file("SOUL.md")
    
    logger.info(f"Session {session_key} initialized with {len(session.core_memory)} chars of context")
    return session
```

---

## Production Examples

### **Example 1: Telegram Bot with Memory**

**File**: `python-agent/app/integrations/telegram_bot.py`

```python
class TelegramBotManager:
    """Telegram bot with persistent memory integration"""
    
    async def handle_message(self, message: dict):
        user_id = message["user_id"]
        text = message["text"]
        
        # 1. Load user's persistent memory
        user_memory = await db.get_user_memory(user_id, memory_type="preference")
        
        # 2. Retrieve relevant facts
        relevant_facts = await vector_store.search(
            text, 
            user_id=user_id,
            limit=5
        )
        
        # 3. Build context-aware prompt
        system_prompt = f"""
        You are a helpful assistant with memory of this user.
        
        User preferences:
        {format_memory(user_memory)}
        
        Relevant facts about this conversation:
        {format_facts(relevant_facts)}
        
        Respond concisely and cite sources when appropriate.
        """
        
        # 4. Generate response with Claude API
        response = await claude.generate(
            system=system_prompt,
            user=text,
            temperature=0.7
        )
        
        # 5. Store this exchange in episodic memory
        await db.add_memory(
            user_id=user_id,
            memory_type="conversation",
            content=f"Q: {text}\nA: {response}",
            importance=calculate_importance(text)
        )
        
        return response
```

### **Example 2: Code Analysis with RAG**

**File**: `python-agent/app/agents/full_workflow.py`

```python
async def analyze_code_with_context(code: str, build_id: str) -> CodeAnalysis:
    """Analyze code using RAG for best practices"""
    
    # 1. Search for similar code patterns
    similar_code = await vector_store.search_similar_code(
        code,
        build_id=build_id,
        n_results=5
    )
    
    # 2. Retrieve documentation
    relevant_docs = await vector_store.search_documentation(
        extract_keywords(code),
        n_results=3
    )
    
    # 3. Get best practices from experience
    best_practices = await vector_store.best_practices_collection.query(
        query_texts=[extract_language(code)],
        n_results=5
    )
    
    # 4. Build analysis prompt with grounding
    prompt = f"""
    Analyze this code for quality and security.
    
    Similar patterns in codebase:
    {format_code_samples(similar_code)}
    
    Relevant best practices:
    {format_practices(best_practices)}
    
    Relevant documentation:
    {format_docs(relevant_docs)}
    
    Code to analyze:
    ```{extract_language(code)}
    {code}
    ```
    
    Provide:
    1. Security issues (with citations)
    2. Code quality improvements
    3. Performance recommendations
    4. References to similar patterns in codebase
    """
    
    # 5. Analyze with grounded context
    analysis = await claude.analyze(prompt)
    
    # 6. Store findings in vector store
    await vector_store.add_code_analysis(build_id, analysis)
    
    return analysis
```

### **Example 3: Memory Consolidation**

**File**: `src/auto-reply/reply/agent-runner-memory.ts`

```typescript
async function runMemoryFlushIfNeeded(params: {
  cfg: OpenClawConfig;
  sessionEntry: SessionEntry;
  sessionKey: string;
}): Promise<SessionEntry | undefined> {
  // Check if memory needs consolidation
  if (!shouldRunMemoryFlush({
    entry: params.sessionEntry,
    contextWindowTokens: 128000,
    softThresholdTokens: 102400  // 80% of context
  })) {
    return undefined;
  }
  
  // Run memory flush (consolidation) turn
  const flushPrompt = `
    You are consolidating session memory for storage.
    
    Session Transcript:
    ${params.sessionEntry.transcript}
    
    Extract and consolidate:
    1. Key decisions made
    2. Important facts learned
    3. User preferences expressed
    4. Actionable learnings
    
    Format as markdown with clear sections.
    Keep it concise (<1000 tokens).
  `;
  
  // Generate consolidation
  const consolidation = await llm.generate(flushPrompt);
  
  // Update persistent memory files
  await updateMemoryFile(
    `.openclaw/workspace/bank/experience.md`,
    consolidation
  );
  
  // Clear old messages from session
  params.sessionEntry.compact();
  
  // Update metadata
  return {
    ...params.sessionEntry,
    memoryFlushAt: Date.now(),
    memoryFlushCompactionCount: params.sessionEntry.compactionCount
  };
}
```

### **Example 4: Hybrid Search Integration**

**File**: `src/agents/memory-search.ts`

```typescript
export async function searchMemory(
  query: string,
  config: ResolvedMemorySearchConfig
): Promise<MemorySearchResult[]> {
  
  // Hybrid search: BM25 + Vector
  const [bm25Results, vectorResults] = await Promise.all([
    db.search_fts(query, limit: config.query.maxResults * 4),
    db.search_vector(
      await embeddings.embed(query),
      limit: config.query.maxResults * 4
    )
  ]);
  
  // Merge with weighting
  const merged = new Map<string, number>();
  
  for (const result of bm25Results) {
    const score = config.query.hybrid.textWeight * result.score;
    merged.set(result.id, (merged.get(result.id) || 0) + score);
  }
  
  for (const result of vectorResults) {
    const score = config.query.hybrid.vectorWeight * (1 - result.distance);
    merged.set(result.id, (merged.get(result.id) || 0) + score);
  }
  
  // Sort and return top-k
  return Array.from(merged.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, config.query.maxResults)
    .map(([id, score]) => ({ id, score }));
}
```

---

## Key Takeaways

### ✅ **Best Practices Summary**

1. **Always Use RAG for Factual Claims**
   - Search memory before answering about facts
   - Include source citations
   - Report confidence scores

2. **Implement Multi-Tier Memory**
   - Layer 1: Context window (short-term)
   - Layer 2: Episodic (conversation history)
   - Layer 3: Semantic (vector-indexed facts)
   - Layer 4: Rules (persistent constraints)

3. **Make Hallucinations Expensive**
   - Require memory search before claims
   - Validate against constraints
   - Use lower temperature (0.3-0.5) for factual tasks
   - Force agent to admit uncertainty

4. **Consolidate Regularly**
   - Memory flush when context > 80% full
   - Extract facts to persistent files
   - Update confidence scores with new evidence
   - Clear old context after consolidation

5. **Use Hybrid Search**
   - Combine BM25 (keywords) + Vector (semantics)
   - Weight by task (50/50 is good default)
   - Index on disk for performance

6. **Make Rules Non-Negotiable**
   - Store in SOUL.md, RULES.md
   - Inject into every prompt
   - Validate responses after generation
   - Use lower temperature to enforce

7. **Document Everything**
   - File paths for citations
   - Confidence scores for facts
   - Reasoning for decisions
   - Evidence links for opinions

---

## References

- **Hindsight Technical Report**: "retain / recall / reflect", four-network memory, confidence evolution
- **Letta/MemGPT**: Core memory blocks + archival memory + tool-driven self-editing
- **SuCo**: arXiv 2411.14754 (2024) - "Subspace Collision" for efficient retrieval
- **OpenClaw**: Production agent system with session management, memory flush, compaction
- **Production Code**: From ultimate-agent workspace (Chroma, LanceDB, SQLite-vec)

---

**Last Updated**: February 3, 2026  
**Status**: ✅ Production-Ready Patterns  
**Version**: 1.0
