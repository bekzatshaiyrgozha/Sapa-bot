import os
import sys
import asyncio
from pathlib import Path
import pytest

# Ensure project root is importable as a package during tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def set_test_env(tmp_path, monkeypatch):
    # Use in-memory sqlite for tests so Postgres is not required
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")
    yield


@pytest.fixture
def anyio_backend():
    return "asyncio"
import os
import asyncio
import pytest


@pytest.fixture(autouse=True)
def set_test_env(tmp_path, monkeypatch):
    # Use in-memory sqlite for tests so Postgres is not required
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")
    yield


@pytest.fixture
def anyio_backend():
    return "asyncio"
