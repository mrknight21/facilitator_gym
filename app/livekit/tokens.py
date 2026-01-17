from livekit import api
from app.core.config import settings

VideoGrants = api.VideoGrants

def build_room_name(session_id: str) -> str:
    return f"sess-{session_id}"

def create_token(api_key: str, api_secret: str, room_name: str, identity: str, grants: api.VideoGrants) -> str:
    token = api.AccessToken(api_key, api_secret) \
        .with_identity(identity) \
        .with_grants(grants) \
        .with_name(identity)
    return token.to_jwt()

def mint_token(identity: str, room_name: str, can_publish: bool, can_subscribe: bool, can_publish_data: bool, room_config: dict | None = None) -> str:
    grant = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=can_publish,
        can_subscribe=can_subscribe,
        can_publish_data=can_publish_data,
    )
    return create_token(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET, room_name, identity, grant)
