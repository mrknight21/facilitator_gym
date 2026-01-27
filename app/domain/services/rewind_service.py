from typing import Optional, List, Any
from app.domain.schemas import RewindPlanRes, ReplayUtteranceView
from app.domain.services.version_control import VersionControl
from app.domain.services.transcript_resolver import TranscriptResolver
from app.db.repos.checkpoint import CheckpointRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.branch import BranchRepo

class RewindService:
    def __init__(
        self,
        vc: VersionControl,
        checkpoint_repo: CheckpointRepo,
        utterance_repo: UtteranceRepo,
        branch_repo: BranchRepo,
        replay_event_repo: Any # Avoid circular import or use forward ref
    ):
        self.vc = vc
        self.checkpoint_repo = checkpoint_repo
        self.utterance_repo = utterance_repo
        self.branch_repo = branch_repo
        self.replay_event_repo = replay_event_repo
        self.resolver = TranscriptResolver(branch_repo, utterance_repo)

    async def create_rewind_plan(
        self,
        session_id: str,
        branch_id: str,
        target_utterance_id: str,
        created_by: str
    ) -> RewindPlanRes:
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Get full transcript to find position
        logger.info(f"Rewind: Getting transcript for session={session_id}, branch={branch_id}")
        view = await self.resolver.get_transcript_view(session_id, branch_id)
        logger.info(f"Rewind: Found {len(view.utterances)} utterances in transcript")
        
        # Find target index
        target_idx = -1
        for i, u in enumerate(view.utterances):
            logger.debug(f"  [{i}] {u.utterance_id}: {u.speaker_id}")
            if u.utterance_id == target_utterance_id:
                target_idx = i
                break
        
        if target_idx < 0:
            logger.error(f"Target {target_utterance_id} not found in utterances: {[u.utterance_id for u in view.utterances]}")
            raise ValueError("Target utterance not found")
        
        logger.info(f"Rewind: Target is at index {target_idx} of {len(view.utterances)}")
        
        # 2. Get Checkpoint BEFORE target - search backwards for any checkpoint
        ckpt = None
        fork_from_utterance_id = None
        
        if target_idx == 0:
            # Target is first utterance, get the first/root checkpoint
            ckpt = await self.checkpoint_repo.get_first(session_id, branch_id)
            logger.info(f"Rewind: Target is first utterance, looking for first checkpoint: {ckpt is not None}")
        else:
            # Search backwards from target-1 to find any checkpoint
            for search_idx in range(target_idx - 1, -1, -1):
                search_utt_id = view.utterances[search_idx].utterance_id
                ckpt = await self.checkpoint_repo.get_by_utterance(session_id, branch_id, search_utt_id)
                if ckpt:
                    fork_from_utterance_id = search_utt_id
                    logger.info(f"Rewind: Found checkpoint at index {search_idx} (utterance {search_utt_id})")
                    break
            
            # If no checkpoint found in direct search, try first checkpoint
            if not ckpt:
                logger.info("Rewind: No checkpoint found before target, trying first checkpoint")
                ckpt = await self.checkpoint_repo.get_first(session_id, branch_id)
        
        if not ckpt:
            logger.error(f"Rewind: No checkpoint found. Listing all checkpoints for branch...")
            all_ckpts = await self.checkpoint_repo.list_by_branch(session_id, branch_id)
            logger.error(f"Rewind: Found {len(all_ckpts)} checkpoints: {[c.get('at_utterance_id') for c in all_ckpts]}")
            raise ValueError("Checkpoint not found before target utterance")
        
        # 3. Fork Branch from the checkpoint BEFORE target
        fork_res = await self.vc.fork_branch(
            session_id, branch_id, 
            fork_from_utterance_id,  # Use the utterance ID where we found the checkpoint
            ckpt["_id"], 
            created_by
        )
        
        # 4. Set Active Branch
        await self.vc.set_active_branch(session_id, fork_res.branch_id)
        
        # 5. Fetch Utterances for Replay - START FROM target (inclusive)
        replay_utterances = []
        handoff_reason = "END_OF_TIMELINE"
        handoff_at_utterance_id = None
        
        for u in view.utterances[target_idx:]:
            # Check for facilitator turn - stop replay here
            if u.kind == "user_intervention":
                handoff_reason = "HIT_FACILITATOR_TURN"
                handoff_at_utterance_id = u.utterance_id
                break
            
            # Add to replay list (including the target turn)
            replay_utterances.append(ReplayUtteranceView(**u.model_dump()))
            
        # 5. Create ReplayEvent (Epic 5)
        import uuid
        import time
        from app.domain.schemas import ReplayStatus
        
        replay_event_id = str(uuid.uuid4())
        replayed_ids = [u.utterance_id for u in replay_utterances]
        
        event_doc = {
            "replay_event_id": replay_event_id,
            "session_id": session_id,
            "from_branch_id": branch_id,
            "to_branch_id": fork_res.branch_id,
            "target_turn_id": target_utterance_id,
            "replayed_turn_ids": replayed_ids,
            "handoff_at_turn_id": handoff_at_utterance_id,
            "handoff_reason": handoff_reason,
            "created_at": str(int(time.time() * 1000)),
            "created_by": created_by,
            "status": ReplayStatus.PLANNED.value
        }
        
        await self.replay_event_repo.create(event_doc)

        return RewindPlanRes(
            new_branch_id=fork_res.branch_id,
            fork_checkpoint_id=ckpt["_id"],
            target_utterance_id=target_utterance_id,
            replay_utterances=replay_utterances,
            handoff_reason=handoff_reason,
            handoff_at_utterance_id=handoff_at_utterance_id,
            replay_event_id=replay_event_id
        )
