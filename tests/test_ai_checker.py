import json
import asyncio

import pytest

from bot.services import ai_checker


class DummyResponse:
    def __init__(self, content):
        self.choices = [type("c", (), {"message": type("m", (), {"content": content})})]


def test_check_presentation_parses_json(monkeypatch):
    # Prepare a fake OpenAI response containing JSON
    expected = {"overall": "ok", "issues": []}
    resp = DummyResponse(json.dumps(expected))

    class FakeCompletions:
        @staticmethod
        def create(*args, **kwargs):
            return resp

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, api_key=None):
            self.chat = FakeChat()

    monkeypatch.setattr(ai_checker, "OpenAI", FakeClient)

    result = ai_checker.check_presentation("=== СЛАЙД 1 ===\nТекст")
    assert isinstance(result, dict)
