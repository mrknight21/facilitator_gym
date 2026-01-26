import asyncio
import time
from dataclasses import dataclass
from typing import Optional, List, Dict
import logging

from app.domain.services.llm_service import LLMService

logger = logging.getLogger(__name__)

@dataclass
class SpecPlan:
    plan_version: int
    after_turn_id: str
    speaker_id: Optional[str]
    text: Optional[str]
    task: asyncio.Task
    
    # Telemetry
    created_at: float = 0.0
    ready_at: float = 0.0

class SpecPlanner:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def plan_next(
        self, 
        history: List[str], 
        personas: Dict[str, str], 
        active_speakers: List[str],
        version: int,
        after_turn_id: str
    ) -> SpecPlan:
        """
        Orchestrates the planning of the next turn.
        Returns a SpecPlan object (populated).
        """
        # Create the plan object shell
        plan = SpecPlan(
            plan_version=version,
            after_turn_id=after_turn_id,
            speaker_id=None,
            text=None,
            task=None, # Assigned by caller usually, but we are inside the task?
            created_at=time.time()
        )
        
        try:
            # 1. Decide Speaker & Generate Text (Consolidated Call - Ticket 6)
            # We assume Ticket 6 is implemented or we use the existing separate calls for now.
            # The plan says Ticket 6 is a dependency for Ticket 4, but we are in Ticket 3.
            # I will implement the logic using the new API `plan_next_turn` which I will add in Ticket 6.
            # For now, I'll assume it exists or implement it in LLMService next.
            
            decision = await self.llm.plan_next_turn(history, personas, active_speakers)
            
            plan.speaker_id = decision.get("speaker_id")
            plan.text = decision.get("text")
            plan.ready_at = time.time()
            
            return plan
            
        except Exception as e:
            logger.error(f"Speculative planning failed: {e}")
            return None
