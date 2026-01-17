from typing import List, Dict, Any
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo
from app.domain.schemas import TranscriptViewOut, UtteranceView, Timing, AudioRef

class TranscriptResolver:
    def __init__(self, branch_repo: BranchRepo, utterance_repo: UtteranceRepo):
        self.branch_repo = branch_repo
        self.utterance_repo = utterance_repo

    async def get_transcript_view(self, session_id: str, branch_id: str) -> TranscriptViewOut:
        # 1. Build branch ancestry
        chain = []
        curr_id = branch_id
        while curr_id:
            branch = await self.branch_repo.get(curr_id)
            if not branch:
                break
            chain.append(branch)
            curr_id = branch.get("parent_branch_id")
        chain.reverse() # [root, ..., target]

        # 2. Collect utterances
        all_utts = []
        
        # Map utterance_id -> display_id for fork point lookup
        utt_display_map = {}
        
        for i, branch in enumerate(chain):
            b_id = branch["_id"]
            is_target = (i == len(chain) - 1)
            
            # Determine cut-off
            limit_utt_id = None
            if not is_target:
                next_branch = chain[i+1]
                limit_utt_id = next_branch.get("fork_from_utterance_id")
            
            # Fetch utterances for this branch
            utts = await self.utterance_repo.get_by_branch(session_id, b_id)
            
            # Filter
            branch_utts = []
            for u in utts:
                branch_utts.append(u)
                if limit_utt_id and u["_id"] == limit_utt_id:
                    break
            
            # Compute display IDs
            parent_fork_disp = None
            if branch.get("parent_branch_id"):
                fork_from = branch.get("fork_from_utterance_id")
                if fork_from and fork_from in utt_display_map:
                    parent_fork_disp = utt_display_map[fork_from]
            
            for u in branch_utts:
                u_id = u["_id"]
                kind = u.get("kind")
                seq = u.get("seq_in_branch", 0)
                
                if kind == "seed":
                    disp = str(u.get("seed_idx", seq))
                else:
                    if parent_fork_disp:
                        disp = f"{parent_fork_disp}.{seq}"
                    else:
                        # Root branch non-seed
                        disp = str(seq)
                
                utt_display_map[u_id] = disp
                
                # Convert to View
                view = UtteranceView(
                    utterance_id=u_id,
                    speaker_id=u.get("speaker_id"),
                    kind=kind,
                    text=u.get("text", ""),
                    timing=Timing(**u.get("timing", {})),
                    audio=AudioRef(**u.get("audio", {})),
                    display_id=disp
                )
                all_utts.append(view)
                
        return TranscriptViewOut(
            session_id=session_id,
            branch_id=branch_id,
            utterances=all_utts
        )
