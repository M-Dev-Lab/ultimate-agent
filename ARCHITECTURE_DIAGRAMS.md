# Ultimate Agent v2.0 - System Architecture Diagram

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     UNIFIED AGENT ORCHESTRATOR                   │
│  (Coordinates all systems, manages lifecycle, provides single API)│
└────────────┬──────────────────┬──────────────────┬────────────────┘
             │                  │                  │
             ▼                  ▼                  ▼
       
    ┌───────────────┐   ┌──────────────┐   ┌───────────────┐
    │ OLLAMA CLIENT │   │ SKILL SYSTEM │   │ MEMORY MANAGER│
    └───────────────┘   └──────────────┘   └───────────────┘
            │                  │                   │
            │ Provides         │ Provides          │ Provides
            │ - Chat API       │ - Routing         │ - Context
            │ - Streaming      │ - Chaining        │ - Recall
            │ - Embeddings     │ - Execution       │ - Storage
            │ - Models         │ - Priority        │ - Analytics
            │ - Health         │ - Weighting       │ - Compression
            │                  │                   │
            └───────────────────┬───────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │  ERROR HANDLER       │
                    │                      │
                    │ - Circuit Breaker    │
                    │ - Recovery Strategy  │
                    │ - Fallback Response  │
                    │ - Error Logging      │
                    └──────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │   USER / TELEGRAM    │
                    │   BOT / API          │
                    └──────────────────────┘
```

## Message Processing Flow

```
User Message (from Telegram/API)
        │
        ▼
┌──────────────────────────────────────┐
│ UNIFIED AGENT: processMessage()      │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ [1] MEMORY: Add user message         │
│     - Store in session memory        │
│     - Calculate importance score     │
│     - Index for semantic search      │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ [2] MEMORY: Get context window       │
│     - Last 50 messages (default)     │
│     - Compressed if > 100 messages   │
│     - Formatted for LLM              │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ [3] SKILL SYSTEM: Route task         │
│     - Extract keywords               │
│     - Match to skills                │
│     - Apply performance weights      │
│     - Rank by relevance              │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ [4] SKILL: Execute best skill        │
│     - Run with timeout               │
│     - Handle errors                  │
│     - Track performance              │
│     - Return result                  │
└──────────────────────────────────────┘
        │
        ▼
    Is chaining enabled?
        │
    ┌───┴───┐
    │       │
   YES     NO
    │       │
    ▼       │
┌───────────┐│
│SKILL:     ││
│Chain      ││
│related    ││
│skills     ││
└───────────┘│
    │       │
    └───┬───┘
        │
        ▼
┌──────────────────────────────────────┐
│ [5] Get Response Content             │
│     - Skill result (if successful)   │
│     - OR Fallback response           │
│     - OR Ollama direct chat          │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ [6] MEMORY: Add assistant response   │
│     - Store in memory                │
│     - Mark as important?             │
│     - Check compression threshold    │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ [7] Return AgentResponse             │
│     {                                │
│       id, content, duration,         │
│       skillsUsed, confidence,        │
│       metadata                       │
│     }                                │
└──────────────────────────────────────┘
        │
        ▼
    Return to User
```

## Skill Routing Algorithm

```
INPUT: User message "Write and test a Node API"

                    ▼
        ┌───────────────────────┐
        │ KEYWORD EXTRACTION    │
        │                       │
        │ "write"   → coding    │
        │ "test"    → testing   │
        │ "API"     → web       │
        └────────┬──────────────┘
                 │
                 ▼
        ┌───────────────────────┐
        │ SKILL MATCHING        │
        │                       │
        │ skill_code:           │
        │   "write" ✓ +1        │
        │   "API" ✓ +1          │
        │   score = 2           │
        │                       │
        │ skill_test:           │
        │   "test" ✓ +1         │
        │   score = 1           │
        │                       │
        │ skill_analyze:        │
        │   score = 0           │
        └────────┬──────────────┘
                 │
                 ▼
        ┌───────────────────────┐
        │ APPLY WEIGHTS         │
        │                       │
        │ skill_code:           │
        │   2 (match) + 1.2     │
        │   (perf weight)       │
        │   = 3.2               │
        │                       │
        │ skill_test:           │
        │   1 (match) + 0.9     │
        │   (perf weight)       │
        │   = 1.9               │
        └────────┬──────────────┘
                 │
                 ▼
        ┌───────────────────────┐
        │ SORT & SELECT         │
        │                       │
        │ 1. skill_code (3.2)   │
        │ 2. skill_test (1.9)   │
        │ 3. skill_analyze(0.0) │
        │                       │
        │ SELECT: skill_code    │
        └────────┬──────────────┘
                 │
                 ▼
        ┌───────────────────────┐
        │ CHECK CHAINING        │
        │                       │
        │ skill_code recommends:│
        │   → skill_test        │
        │   → skill_analyze     │
        │                       │
        │ Execute chained skills│
        └────────┬──────────────┘
                 │
                 ▼
        EXECUTE: skill_code
              → skill_test
              → skill_analyze
```

## Circuit Breaker State Machine

```
                    ┌─────────────┐
                    │  CLOSED     │
               ┌────│  (OK)       │────┐
               │    │ Requests OK │    │
               │    │ No failures │    │
               │    └─────────────┘    │
               │          ▲            │
               │          │            │
          [recovery]   [5+ failures]   │
               │          │            │
               │          ▼            │
               │    ┌─────────────┐    │
               │    │  OPEN       │    │
               │    │ (Failing)   │    │
               │    │ Block calls │    │
               │    │ Use fallback│    │
               │    └─────────────┘    │
               │          │            │
               │      [60s timeout]    │
               │          │            │
               │          ▼            │
               │    ┌─────────────┐    │
               │    │HALF-OPEN    │    │
               │    │(Testing)    │    │
               │    │Allow 1 call │    │
               │    └─────────────┘    │
               │      │        │       │
        [failure]  [success]  │       │
               │      │        │       │
               │      │    [2+ success]
               │      │        │       │
               │      ▼        ▼       │
               └──────→ CLOSED ←───────┘
```

## Error Recovery Strategy Priority

```
ERROR OCCURS
        │
        ▼
┌──────────────────────────────┐
│ CLASSIFY ERROR               │
├──────────────────────────────┤
│ Network    │ Timeout         │
│ NotFound   │ ServerError     │
│ Auth       │ RateLimit       │
│ Memory     │ Parsing         │
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ MATCH RECOVERY STRATEGIES            │
├──────────────────────────────────────┤
│ 1. ConnectionRetry (Priority: 10)    │
│    └─ Wait 1s, retry                 │
│                                      │
│ 2. TimeoutRetry (Priority: 9)        │
│    └─ Wait 2s, retry                 │
│                                      │
│ 3. DemoModeFallback (Priority: 1)    │
│    └─ Return cached response         │
└──────────────────────────────────────┘
        │
        ▼
TRY STRATEGY (Priority Order)
        │
    ┌───┴──────────────┐
    │                  │
   YES ─ SUCCESS        NO ─ NEXT
    │                  │
    ▼                  ▼
RETURN RESULT      TRY NEXT
                   STRATEGY
```

## Memory Compression Example

```
BEFORE COMPRESSION
┌─────────────────────────────────────────┐
│ Message 1: "How do I use Node.js?"      │ (timestamp: t1)
│ Message 2: "Here's the basics..."       │ (timestamp: t2)
│ ...                                     │
│ Message 97: "Let me try that..."        │ (timestamp: t97)
│ Message 98: "Great, it works!"          │ (timestamp: t98)
│ Message 99: "Any final tips?"           │ (timestamp: t99)
│ Message 100: "Yes, here are tips..."    │ (timestamp: t100)
│ Message 101: "Thanks!"                  │ (timestamp: t101)
│ ...                                     │
│ (150 messages total, 500KB)             │
└─────────────────────────────────────────┘

                    │
            [Compression triggered]
        [Keep: last 30 messages only]
        [Compress: first 120 messages]
                    │
                    ▼

AFTER COMPRESSION
┌─────────────────────────────────────────┐
│ [COMPRESSED: 120 messages about Node.js,│
│  async/await, error handling, testing   │
│  discussed from t1 to t120. Key points: │
│  basic setup, async patterns, best      │
│  practices for production code]         │
│                                         │
│ Message 21: "What about databases?"     │ (timestamp: t80)
│ ...                                     │
│ Message 30: "Thanks!"                   │ (timestamp: t101)
│                                         │
│ (31 messages total, 98KB)               │
└─────────────────────────────────────────┘

SAVINGS:
- Size: 500KB → 98KB (80% reduction)
- Messages: 150 → 31 (79% reduction)
- Context preserved in summary
```

## System Dependencies

```
┌──────────────────────────────────────┐
│        UNIFIED AGENT                 │
├──────────────────────────────────────┤
│                                      │
│  requires                            │
│  ├─ OllamaClient                     │
│  ├─ SkillSystem                      │
│  ├─ MemoryManager                    │
│  └─ ErrorHandler                     │
│                                      │
└──────────────────────────────────────┘
         │        │        │        │
         ▼        ▼        ▼        ▼
    ┌────────────────────────────────────┐
    │ OllamaClient                       │
    ├────────────────────────────────────┤
    │ requires:                          │
    │ ├─ axios (HTTP client)             │
    │ └─ EventEmitter (events)           │
    │                                    │
    │ provides:                          │
    │ ├─ chat(messages)                  │
    │ ├─ chatStream(messages)            │
    │ ├─ embed(text)                     │
    │ └─ getStats()                      │
    └────────────────────────────────────┘

    ┌────────────────────────────────────┐
    │ SkillSystem                        │
    ├────────────────────────────────────┤
    │ requires:                          │
    │ ├─ OllamaClient (for execution)    │
    │ └─ EventEmitter (events)           │
    │                                    │
    │ provides:                          │
    │ ├─ executeSkill(id, input)         │
    │ ├─ routeTask(task, input)          │
    │ ├─ chainSkills(ids, input)         │
    │ └─ getSkillStats()                 │
    └────────────────────────────────────┘

    ┌────────────────────────────────────┐
    │ MemoryManager                      │
    ├────────────────────────────────────┤
    │ requires:                          │
    │ ├─ fs/promises (file I/O)          │
    │ └─ EventEmitter (events)           │
    │                                    │
    │ provides:                          │
    │ ├─ getOrCreateSession()            │
    │ ├─ addMessage()                    │
    │ ├─ getContextWindow()              │
    │ ├─ retrieveSimilar()               │
    │ └─ getStats()                      │
    └────────────────────────────────────┘

    ┌────────────────────────────────────┐
    │ ErrorHandler                       │
    ├────────────────────────────────────┤
    │ requires:                          │
    │ ├─ fs/promises (logging)           │
    │ └─ EventEmitter (events)           │
    │                                    │
    │ provides:                          │
    │ ├─ handleError(error, context)     │
    │ ├─ recordSuccess(service)          │
    │ ├─ recordFailure(service)          │
    │ ├─ isCircuitOpen(service)          │
    │ └─ getStats()                      │
    └────────────────────────────────────┘
```

## Data Flow: Complete Interaction

```
TELEGRAM USER
     │
     │ "Write a function"
     ▼
┌──────────────┐
│ TELEGRAM BOT │
└──────┬───────┘
       │
       │ agent.processMessage()
       ▼
┌──────────────────────────────────────────────┐
│ UNIFIED AGENT                                │
│                                              │
│ 1. Create/Get session                        │
│ 2. Add message to memory                     │
│ 3. Get context (last 50 messages)            │
│ 4. Extract topic/urgency                     │
│ 5. Route to best skill                       │
│ 6. Execute skill (with timeout)              │
│ 7. Check error → recover if needed           │
│ 8. Get response content                      │
│ 9. Add to memory                             │
│ 10. Return to user                           │
└──────┬───────────────────────────────────────┘
       │
       ├─────────────────────────────┬──────────────────┐
       ▼                             ▼                  ▼
    ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
    │ OLLAMA      │    │ SKILL SYSTEM     │    │ MEMORY      │
    │             │    │                  │    │             │
    │ Chat API    │    │ Route:           │    │ Store:      │
    │ ├─ Request  │    │ ├─ skill_code    │    │ ├─ User msg │
    │ ├─ Retry    │    │ ├─ skill_test    │    │ ├─ Response │
    │ ├─ Stream   │    │ ├─ skill_debug   │    │ ├─ Context  │
    │ └─ Response │    │ └─ skill_analyze │    │ ├─ Topic    │
    │             │    │                  │    │ └─ Importance
    │ Cache:      │    │ Execute:         │    │             │
    │ ├─ Check    │    │ ├─ Run skill     │    │ Recall:     │
    │ ├─ Store    │    │ ├─ Error handle  │    │ ├─ Context  │
    │ └─ Reuse    │    │ ├─ Update weight │    │ ├─ Similar  │
    │             │    │ └─ Track perf    │    │ └─ Semantic │
    └─────────────┘    └──────────────────┘    └─────────────┘
       │                       │                     │
       │                       │ Error occurs?       │
       │                       └─────────┬───────────┘
       │                                 ▼
       │                        ┌──────────────────┐
       │                        │ ERROR HANDLER    │
       │                        │                  │
       │                        │ Categorize:      │
       │                        │ ├─ Network       │
       │                        │ ├─ Timeout       │
       │                        │ ├─ API Error     │
       │                        │ └─ Other         │
       │                        │                  │
       │                        │ Circuit Breaker: │
       │                        │ ├─ Record fail   │
       │                        │ ├─ Check open    │
       │                        │ └─ Update state  │
       │                        │                  │
       │                        │ Recovery:        │
       │                        │ ├─ Retry         │
       │                        │ ├─ Fallback      │
       │                        │ └─ Demo mode     │
       │                        │                  │
       │                        │ Logging:         │
       │                        │ ├─ Store error   │
       │                        │ ├─ Track rate    │
       │                        │ └─ Emit event    │
       │                        └──────────────────┘
       │                                 │
       └─────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ RESPONSE READY       │
         │                      │
         │ {                    │
         │   id: "...",         │
         │   content: "...",    │
         │   skillsUsed: [...], │
         │   duration: 2400ms,  │
         │   confidence: 0.92,  │
         │   metadata: {...}    │
         │ }                    │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ TELEGRAM BOT         │
         │                      │
         │ await ctx.reply(     │
         │   response.content   │
         │ )                    │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ TELEGRAM USER        │
         │                      │
         │ Receives response    │
         │ in chat              │
         └──────────────────────┘
```

---

**These diagrams show**:
- System architecture and relationships
- Message processing pipeline
- Skill routing algorithm
- Circuit breaker state machine
- Error recovery strategy selection
- Memory compression example
- System dependencies
- Complete interaction data flow

**For detailed information, see**:
- `ARCHITECTURE_V2.md` - Complete technical documentation
- `QUICKSTART_v2.md` - 5-minute setup guide
- `IMPLEMENTATION_COMPLETE_v2.md` - What was built

---

**Version**: 2.0.0  
**Status**: ✅ Production Ready  
**Last Updated**: February 4, 2025
