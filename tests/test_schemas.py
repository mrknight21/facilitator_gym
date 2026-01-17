from app.domain.schemas import TurnBidMsg

def test_turn_bid_schema_roundtrip():
    msg = TurnBidMsg(session_id="s", branch_id="b", agent_id="alice", bid=0.5, intent="ask", rationale="")
    d = msg.model_dump()
    msg2 = TurnBidMsg.model_validate(d)
    assert msg2.bid == 0.5
