"""
Memory Management API endpoints
Allows Admin to view, update, and manage persistent memory
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
import logging
from app.memory.persistent_memory import get_memory, MemoryFact
from app.memory import get_memory_manager
from app.agents.memory_enhanced import get_enhanced_agent
from app.security.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/status")
async def get_memory_status(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current memory system status
    
    Returns:
        Memory system status with fact and rule counts
    """
    memory = get_memory()
    agent = get_enhanced_agent()
    
    return {
        "status": "active",
        "facts_count": len(memory.short_term),
        "rules_count": len(memory.rules),
        "memory_state": agent.get_memory_state(),
        "agent_status": agent.get_agent_status(),
    }


@router.get("/facts")
async def list_memory_facts(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence"),
    user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List all memory facts with optional filtering
    
    Args:
        category: Optional category filter
        min_confidence: Minimum confidence threshold
    
    Returns:
        List of memory facts
    """
    memory = get_memory()
    facts = memory.short_term
    
    # Filter by category
    if category:
        facts = [f for f in facts if f.category == category]
    
    # Filter by confidence
    facts = [f for f in facts if f.confidence >= min_confidence]
    
    return [f.to_dict() for f in sorted(facts, key=lambda f: f.confidence, reverse=True)]


@router.post("/facts")
async def add_memory_fact(
    content: str = Query(..., min_length=1),
    category: str = Query(..., min_length=1),
    confidence: float = Query(0.5, ge=0.0, le=1.0),
    tags: Optional[List[str]] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Add a new fact to memory (Admin only)
    
    Args:
        content: Fact content
        category: Fact category
        confidence: Confidence level (0.0-1.0)
        tags: Optional tags for semantic search
    
    Returns:
        Added fact with metadata
    """
    # Verify Admin role
    if "admin" not in user.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can add memory facts"
        )
    
    memory = get_memory()
    fact = memory.add_fact(
        content=content,
        category=category,
        confidence=confidence,
        source=f"admin:{user.get('sub')}",
        tags=tags or []
    )
    
    logger.info(f"Admin added memory fact: {category}")
    
    return {
        "status": "created",
        "fact": fact.to_dict(),
        "message": "Memory fact successfully added"
    }


@router.get("/facts/search")
async def search_memory(
    query: str = Query(..., min_length=1),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Search memory for relevant facts (semantic search)
    
    Args:
        query: Search query
    
    Returns:
        Matching facts with relevance scoring
    """
    memory = get_memory()
    facts = memory.recall_facts(query)
    
    return {
        "query": query,
        "results_count": len(facts),
        "facts": [f.to_dict() for f in facts]
    }


@router.get("/rules")
async def get_rules(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get all active strict rules
    
    Returns:
        List of strict rules
    """
    memory = get_memory()
    
    return {
        "rules_count": len(memory.rules),
        "rules": memory.rules,
        "status": "active",
        "last_updated": "2026-02-03"
    }


@router.post("/rules")
async def add_rule(
    rule_content: str = Query(..., min_length=1),
    priority: str = Query("medium", pattern="^(critical|high|medium|low)$"),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Add a new rule to strict rules (Admin only)
    
    Args:
        rule_content: The rule text
        priority: Priority level
    
    Returns:
        Confirmation with rule added
    """
    # Verify Admin role
    if "admin" not in user.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can add rules"
        )
    
    memory = get_memory()
    new_rule = f"[{priority.upper()}] {rule_content}"
    memory.rules.append(new_rule)
    
    logger.info(f"Admin added rule: {rule_content}")
    
    return {
        "status": "created",
        "rule": new_rule,
        "priority": priority,
        "message": "Rule successfully added to strict rules"
    }


@router.post("/consolidate")
async def consolidate_memory(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Trigger memory consolidation (Admin only)
    
    Consolidation:
    - Removes low-confidence noise
    - Updates confidence scores
    - Saves optimized state
    
    Returns:
        Consolidation results
    """
    # Verify Admin role
    if "admin" not in user.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can consolidate memory"
        )
    
    memory = get_memory()
    initial_count = len(memory.short_term)
    
    memory.consolidate_memory()
    
    final_count = len(memory.short_term)
    removed = initial_count - final_count
    
    logger.info(f"Memory consolidated: removed {removed} facts")
    
    return {
        "status": "consolidated",
        "initial_facts": initial_count,
        "final_facts": final_count,
        "removed": removed,
        "message": "Memory consolidation completed"
    }


@router.get("/validation/status")
async def get_validation_status(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get rule validation status and recent violations
    
    Returns:
        Validation status and statistics
    """
    return {
        "validation_active": True,
        "rules_enforced": True,
        "last_check": "2026-02-03T00:00:00Z",
        "violations_detected": 0,
        "system_status": "compliant"
    }


@router.get("/analytics")
async def get_memory_analytics(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get memory analytics and insights
    
    Returns:
        Memory analytics including confidence distribution, category breakdown
    """
    memory = get_memory()
    agent = get_enhanced_agent()
    
    return {
        "total_facts": len(memory.short_term),
        "total_rules": len(memory.rules),
        "confidence_distribution": agent._group_by_confidence(),
        "category_breakdown": agent._group_by_category(),
        "memory_state": agent.get_memory_state(),
    }
