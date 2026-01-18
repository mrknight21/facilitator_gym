from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os
from typing import Optional

# Explicitly load .env.local
load_dotenv(".env.local")

class Settings(BaseSettings):
    MONGO_URI: str
    MONGO_DB: str = "sim"
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    OPENAI_API_KEY: Optional[str] = None
    ELEVEN_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

settings = Settings()
