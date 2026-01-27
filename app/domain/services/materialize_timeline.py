from typing import List, Dict, Any, Literal
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.replay_event_repo import ReplayEventRepo
from app.domain.services.transcript_resolver import TranscriptResolver
import logging

logger = logging.getLogger(__name__)

class MaterializedItem:
    """Represents an item in a materialized timeline."""
    def __init__(
        self, 
        turn_id: str, 
        speaker_id: str, 
        text: str, 
        audio: Dict[str, Any], 
        source: Literal["original", "replayed", "new"],
        replay_event_id: str = None
    ):
        self.turn_id = turn_id
        self.speaker_id = speaker_id
        self.text = text
        self.audio = audio
        self.source = source
        self.replay_event_id = replay_event_id

    def to_dict(self):
        return {
            "turn_id": self.turn_id,
            "speaker_id": self.speaker_id,
            "text": self.text,
            "audio": self.audio,
            "source": self.source,
            "replay_event_id": self.replay_event_id
        }


class MaterializeTimelineService:
    def __init__(
        self,
        branch_repo: BranchRepo,
        utterance_repo: UtteranceRepo,
        replay_event_repo: ReplayEventRepo,
        resolver: TranscriptResolver
    ):
        self.branch_repo = branch_repo
        self.utterance_repo = utterance_repo
        self.replay_event_repo = replay_event_repo
        self.resolver = resolver

    async def get_materialized_timeline(
        self, 
        session_id: str, 
        branch_id: str
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct the full timeline for a branch, including virtual replays.
        
        Returns ordered items:
        1. Base turns from branch up to divergence (source: original)
        2. Virtual replay blocks from replay_events (source: replayed)
        3. New turns stored in this branch after divergence (source: new)
        """
        result = []
        
        # 1. Get the branch info to find parent/fork point
        branch = await self.branch_repo.get(session_id, branch_id)
        if not branch:
            logger.warning(f"Branch {branch_id} not found")
            return []
        
        parent_branch_id = branch.get("parent_id")
        forked_at_utterance_id = branch.get("forked_at_utterance_id")
        
        # 2. Get replay events targeting this branch
        replay_events = await self.replay_event_repo.list_by_branch(session_id, branch_id)
        
        # 3. Get all utterances for THIS branch (new turns after fork)
        new_turns = await self.utterance_repo.get_by_branch(session_id, branch_id)
        
        # 4. If this is not a forked branch, just return the utterances as "original"
        if not parent_branch_id or not forked_at_utterance_id:
            for u in new_turns:
                result.append(MaterializedItem(
                    turn_id=u["_id"],
                    speaker_id=u.get("speaker_id"),
                    text=u.get("text", ""),
                    audio=u.get("audio", {}),
                    source="original"
                ).to_dict())
            return result
        
        # 5. Get base turns from parent branch up to fork point
        parent_view = await self.resolver.get_transcript_view(session_id, parent_branch_id)
        found_fork = False
        for u in parent_view.utterances:
            result.append(MaterializedItem(
                turn_id=u.utterance_id,
                speaker_id=u.speaker_id,
                text=u.text,
                audio=u.audio.model_dump() if u.audio else {},
                source="original"
            ).to_dict())
            if u.utterance_id == forked_at_utterance_id:
                found_fork = True
                break
        
        # 6. Inject replay blocks (from replay_events)
        for evt in replay_events:
            if evt.get("status") not in ["completed", "canceled"]:
                continue  # Only include completed/canceled replays
            
            # Get the replayed turns from the source branch
            replayed_ids = evt.get("replayed_turn_ids", [])
            from_branch_id = evt.get("from_branch_id")
            
            for turn_id in replayed_ids:
                # Fetch the original utterance
                u = await self.utterance_repo.col.find_one({"_id": turn_id})
                if u:
                    result.append(MaterializedItem(
                        turn_id=u["_id"],
                        speaker_id=u.get("speaker_id"),
                        text=u.get("text", ""),
                        audio=u.get("audio", {}),
                        source="replayed",
                        replay_event_id=evt.get("replay_event_id")
                    ).to_dict())
        
        # 7. Append new turns (stored in this branch after divergence)
        for u in new_turns:
            result.append(MaterializedItem(
                turn_id=u["_id"],
                speaker_id=u.get("speaker_id"),
                text=u.get("text", ""),
                audio=u.get("audio", {}),
                source="new"
            ).to_dict())
        
        return result
