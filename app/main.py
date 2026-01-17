from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
from app.api import case_studies, sessions, branches, transcripts, checkpoints, metrics, livekit, utterances, intervene, rewind

from fastapi.middleware.cors import CORSMiddleware

setup_logging()

app = FastAPI(title="Facilitator Gym Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for prototype
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(case_studies.router)
app.include_router(sessions.router)
app.include_router(branches.router)
app.include_router(transcripts.router)
app.include_router(checkpoints.router)
app.include_router(metrics.router)
app.include_router(livekit.router)
app.include_router(utterances.router)
app.include_router(intervene.router)
app.include_router(rewind.router)

@app.get("/")
async def root():
    return {"message": "Hello World", "config_loaded": bool(settings.MONGO_URI)}
