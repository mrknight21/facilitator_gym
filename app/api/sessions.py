from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.domain.schemas import SessionStartReq, SessionStartRes
from app.domain.services.session_manager import SessionManager
from app.db.repos.session import SessionRepo
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.case_study import CaseStudyRepo

router = APIRouter()

# Global registry of active simulation tasks
# In a real production app with multiple workers, this would need Redis/Celery
active_simulations: dict[str, asyncio.Task] = {}

def get_session_manager():
    return SessionManager(SessionRepo(), BranchRepo(), UtteranceRepo(), CaseStudyRepo())

@router.post("/sessions/start", response_model=SessionStartRes)
async def start_session(
    req: SessionStartReq, 
    mgr: SessionManager = Depends(get_session_manager)
):
    try:
        res = await mgr.start_session(req)
        
        # Spawn Conductor and Agents in background
        # We use asyncio.create_task to keep a reference for cancellation
        task = asyncio.create_task(spawn_simulation(res.session_id, res.active_branch_id, res.room_name))
        active_simulations[res.session_id] = task
        
        # Cleanup callback
        def on_done(t):
            if res.session_id in active_simulations:
                del active_simulations[res.session_id]
        task.add_done_callback(on_done)
        
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    if session_id not in active_simulations:
        # It might have already finished or never started
        return {"status": "already_stopped"}
    
    task = active_simulations[session_id]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    return {"status": "stopped"}

from app.livekit.conductor import Conductor
from app.livekit.agent_worker import AgentWorker
from app.core.config import settings
from app.domain.services.conductor_writer import ConductorWriter
from app.metrics.engine import MetricsEngine
from app.domain.services.transcript_resolver import TranscriptResolver
from app.db.repos.session import SessionRepo
from app.db.repos.branch import BranchRepo
from app.db.repos.utterance import UtteranceRepo
from app.db.repos.checkpoint import CheckpointRepo
from app.db.repos.metrics import MetricsRepo
from app.livekit.tokens import create_token, VideoGrants
import asyncio
import logging

logger = logging.getLogger(__name__)

async def spawn_simulation(session_id: str, branch_id: str, room_name: str):
    logger.info(f"Spawning simulation for session {session_id}")

    # 1. Init Repos
    session_repo = SessionRepo()
    branch_repo = BranchRepo()
    utterance_repo = UtteranceRepo()
    checkpoint_repo = CheckpointRepo()
    metrics_repo = MetricsRepo()

    # 2. Init Services
    resolver = TranscriptResolver(branch_repo, utterance_repo)
    writer = ConductorWriter(session_repo, branch_repo, utterance_repo, checkpoint_repo, resolver)
    metrics = MetricsEngine(metrics_repo, utterance_repo, resolver)
    
    conductor = Conductor(writer, metrics, resolver)
    
    # 2. Connect Conductor
    token = create_token(
        settings.LIVEKIT_API_KEY, 
        settings.LIVEKIT_API_SECRET, 
        room_name, 
        "conductor-bot", 
        VideoGrants(room_join=True, room_admin=True, room=room_name)
    )
    await conductor.connect(settings.LIVEKIT_URL, token, session_id, branch_id)
    
    # 3. Connect Agents (Hardcoded for now based on prototype)
    agents = []
    for name in ["alice", "bob", "charlie"]:
        agent = AgentWorker(name, "helpful")
        agent_token = create_token(
            settings.LIVEKIT_API_KEY, 
            settings.LIVEKIT_API_SECRET, 
            room_name, 
            name, 
            VideoGrants(room_join=True, room=room_name)
        )
        await agent.connect(settings.LIVEKIT_URL, agent_token)
        agents.append(agent)

    # 4. Start Seed Playback
    await conductor.start_seed_playback()

    # Keep alive (simple loop for prototype)
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Simulation stopped")
        await conductor.disconnect()
        for a in agents:
            await a.disconnect()
