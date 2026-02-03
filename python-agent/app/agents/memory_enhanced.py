"""
Enhanced agent with persistent memory integration
Implements best practices for hallucination prevention and knowledge grounding
"""

import logging
from typing import Dict, Any, Optional, List
from app.memory import get_memory_manager
from app.memory.persistent_memory import get_memory

logger = logging.getLogger(__name__)


class MemoryAugmentedAgent:
    """
    Agent enhanced with persistent memory and strict rule enforcement
    
    Features:
    - Memory-first reasoning (check memory before answering)
    - Hallucination prevention through fact grounding
    - Strict rule enforcement
    - Confidence-bearing responses
    - Citation of sources
    """

    def __init__(self):
        """Initialize the enhanced agent"""
        self.memory = get_memory()
        self.manager = get_memory_manager()
        self.rules_validated = False

    def enhance_prompt(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Enhance user prompt with memory and rules
        
        Implements memory-first approach:
        1. Retrieve relevant facts from memory
        2. Validate against rules
        3. Inject into prompt for grounding
        
        Args:
            user_query: User's input query
            context: Optional additional context
        
        Returns:
            Enhanced prompt with memory and rule context
        """
        prompt_parts = []
        
        # 1. System rules (ALWAYS at top)
        prompt_parts.append("## 🔒 OPERATIONAL CONSTRAINTS")
        prompt_parts.append(self.memory.get_rules_context())
        
        # 2. Memory retrieval (memory-augmented generation)
        prompt_parts.append("\n## 📚 RELEVANT FACTS FROM MEMORY")
        memory_context = self.memory.get_memory_context(query=user_query, max_facts=5)
        prompt_parts.append(memory_context)
        
        # 3. User query with grounding instruction
        prompt_parts.append("\n## ❓ YOUR TASK")
        prompt_parts.append("Before answering, verify your knowledge using the facts above.")
        prompt_parts.append("If a claim isn't in memory, explicitly state your uncertainty.\n")
        prompt_parts.append(f"User Query: {user_query}")
        
        # 4. Optional context
        if context:
            prompt_parts.append("\n## 📋 ADDITIONAL CONTEXT")
            for key, value in context.items():
                prompt_parts.append(f"- {key}: {value}")
        
        return "\n".join(prompt_parts)

    def process_response(self, response: str, interaction_type: str = "general") -> Dict[str, Any]:
        """
        Post-process agent response with validation and memory update
        
        Args:
            response: Agent's generated response
            interaction_type: Type of interaction (e.g., "code", "explanation", "analysis")
        
        Returns:
            Processed response with metadata
        """
        result = {
            "response": response,
            "is_valid": True,
            "violations": [],
            "confidence": 1.0,
            "memory_updated": False,
        }
        
        # Validate against strict rules
        is_valid, violation = self.memory.validate_against_rules(response)
        if not is_valid:
            result["is_valid"] = False
            result["violations"].append(violation)
            logger.warning(f"Rule violation detected: {violation}")
        
        # Extract learnings (high-confidence facts to remember)
        if interaction_type == "code" and result["is_valid"]:
            self._extract_code_patterns(response)
        elif interaction_type == "analysis":
            self._extract_insights(response)
        
        return result

    def _extract_code_patterns(self, code_response: str):
        """Extract code patterns and best practices from response"""
        patterns_found = []
        
        # Detect successful patterns
        if "Annotated[str, StringConstraints" in code_response:
            patterns_found.append("Pydantic v2 StringConstraints pattern")
        
        if "field_validator" in code_response and "@classmethod" in code_response:
            patterns_found.append("Pydantic v2 field_validator with classmethod")
        
        if "sqlalchemy.text()" in code_response:
            patterns_found.append("SQLAlchemy text() for raw SQL safety")
        
        if "@app.on_event(" in code_response:
            patterns_found.append("FastAPI lifecycle event management")
        
        # Add patterns to memory
        for pattern in patterns_found:
            self.memory.add_fact(
                content=pattern,
                category="code_pattern",
                confidence=0.95,
                source="agent_generation",
                tags=["code", "best_practice"]
            )
            logger.info(f"Learned pattern: {pattern}")

    def _extract_insights(self, analysis_response: str):
        """Extract insights and learnings from analysis"""
        # Extract key statements (simplified approach)
        sentences = analysis_response.split('.')
        
        for sentence in sentences[:3]:  # Top 3 sentences
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 200:
                self.memory.add_fact(
                    content=sentence,
                    category="insight",
                    confidence=0.7,
                    source="agent_analysis",
                    tags=["analysis", "learning"]
                )

    def get_memory_state(self) -> Dict[str, Any]:
        """Get current memory state for debugging"""
        return {
            "total_facts": len(self.memory.short_term),
            "total_rules": len(self.memory.rules),
            "facts_by_confidence": self._group_by_confidence(),
            "facts_by_category": self._group_by_category(),
        }

    def _group_by_confidence(self) -> Dict[str, int]:
        """Group facts by confidence level"""
        groups = {"high": 0, "medium": 0, "low": 0}
        for fact in self.memory.short_term:
            if fact.confidence >= 0.9:
                groups["high"] += 1
            elif fact.confidence >= 0.7:
                groups["medium"] += 1
            else:
                groups["low"] += 1
        return groups

    def _group_by_category(self) -> Dict[str, int]:
        """Group facts by category"""
        groups = {}
        for fact in self.memory.short_term:
            groups[fact.category] = groups.get(fact.category, 0) + 1
        return groups

    def add_admin_note(self, note: str, category: str = "admin_note", 
                       priority: int = 1) -> bool:
        """
        Add an admin note to persistent memory
        
        Args:
            note: The note content
            category: Category of the note
            priority: Priority level (1=high, 5=low)
        
        Returns:
            Success status
        """
        try:
            self.memory.add_fact(
                content=note,
                category=category,
                confidence=0.99,  # Admin notes are high confidence
                source="admin",
                tags=["admin", f"priority_{priority}"]
            )
            logger.info(f"✅ Admin note added: {note[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error adding admin note: {e}")
            return False

    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status including memory state"""
        return {
            "status": "operational",
            "memory": self.get_memory_state(),
            "rules_active": len(self.memory.rules) > 0,
            "rules_count": len(self.memory.rules),
            "facts_count": len(self.memory.short_term),
            "memory_validation_active": True,
        }


# Global agent instance
_enhanced_agent: Optional[MemoryAugmentedAgent] = None


def get_enhanced_agent() -> MemoryAugmentedAgent:
    """Get or create the enhanced agent instance"""
    global _enhanced_agent
    if _enhanced_agent is None:
        _enhanced_agent = MemoryAugmentedAgent()
    return _enhanced_agent


def init_enhanced_agent():
    """Initialize the enhanced agent on startup"""
    agent = get_enhanced_agent()
    logger.info(f"✅ Enhanced agent initialized with memory system")
    return agent
