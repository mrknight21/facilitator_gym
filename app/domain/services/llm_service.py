import json
import logging
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set. LLMService will fail.")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def decide_speaker(self, history: List[str], personas: Dict[str, str], active_speakers: List[str]) -> Dict:
        """
        Decides who speaks next or if silence is appropriate.
        Returns: {"speaker_id": "alice" | "bob" | ... | "silence", "reason": "..."}
        """
        system_prompt = (
            "You are a conversation director for a simulation. "
            "Your job is to decide who should speak next based on the history and personas. "
            "You can also choose 'silence' if it's natural for the conversation to pause or if the facilitator should intervene. "
            "Output valid JSON only: {\"speaker_id\": \"<id>\", \"reason\": \"<chain_of_thought>\"}"
        )
        
        user_content = f"""
        Active Speakers: {', '.join(active_speakers)}
        
        Personas:
        {json.dumps(personas, indent=2)}
        
        Recent History:
        {self._format_history(history)}
        
        Who should speak next? Choose one of {active_speakers} or 'silence'.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o", # High intelligence for control logic
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM Decision Error: {e}")
            # Fallback to silence
            return {"speaker_id": "silence", "reason": "Error fallback"}

    async def generate_turn_text(self, speaker_id: str, persona: str, history: List[str]) -> str:
        """
        Generates text for the speaker.
        """
        system_prompt = (
            f"You are {speaker_id}. Roleplay this persona accurately. "
            f"Persona: {persona}\n"
            "Keep your response natural, conversational, and concise (1-2 sentences). "
            "Do not start with 'Alice:' or 'Bob:'. Just the text."
        )
        
        user_content = f"""
        Recent History:
        {self._format_history(history)}
        
        Respond to the conversation.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini", # Faster/Cheaper for text gen
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM Generation Error: {e}")
            return "I have nothing to add right now."

    def _format_history(self, history: List[str]) -> str:
        # History is expected to be a list of "Speaker: Text" strings
        return "\n".join(history[-10:])
