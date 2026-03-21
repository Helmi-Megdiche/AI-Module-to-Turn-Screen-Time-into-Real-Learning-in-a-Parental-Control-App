"""Shared pytest fixtures for ai-service."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_moderation_lru_cache() -> None:
    """Defer importing moderation_service until tests run (heavy deps e.g. transformers)."""
    import app.services.moderation_service as moderation_service

    yield
    moderation_service._classify_zero_shot_cached.cache_clear()
