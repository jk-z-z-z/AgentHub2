import json

from app.services.message_service import _extract_agent_mentions


def test_extract_agent_mentions_empty() -> None:
    assert _extract_agent_mentions("") == []
    assert _extract_agent_mentions("{}") == []


def test_extract_agent_mentions_happy_path() -> None:
    meta = {
        "mentions": [
            {"kind": "agent", "member_id": 10},
            {"kind": "user", "member_id": 11},
            {"kind": "agent", "member_id": "12"},
            {"kind": "agent", "member_id": 10},
        ]
    }
    assert _extract_agent_mentions(json.dumps(meta)) == [10, 12]


def test_extract_agent_mentions_invalid_json() -> None:
    assert _extract_agent_mentions("{not-json") == []
