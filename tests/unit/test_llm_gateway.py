"""Unit tests for Centralized LLM Gateway mode enforcement and provenance tracking."""
import pytest
from unittest.mock import patch
from backend.app.services.llm_service import llm_service
from backend.app.core.exceptions import AppException
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_llm_mock_mode_returns_simulated_provenance():
    """Verify that in mock mode, LLM gateway produces explicit simulation metadata."""
    with patch.object(settings, "LLM_MODE", "mock"):
        messages = [{"role": "user", "content": "Analyze supply chain risk for port congestion."}]
        response = await llm_service.chat_completion(messages=messages, temperature=0.2)

        assert response["content"] is not None
        assert len(response["content"]) > 0
        assert response["metadata"]["mode"] == "SIMULATED"
        assert response["metadata"]["is_synthetic"] is True
        assert response["metadata"]["provider"] == "mock"


@pytest.mark.asyncio
async def test_llm_live_mode_without_key_fails_fast():
    """Verify that in live mode, missing API key fails fast with 503 instead of silent mocking."""
    with patch.object(settings, "LLM_MODE", "live"):
        with patch.object(settings, "OPENAI_API_KEY", ""):
            messages = [{"role": "user", "content": "Evaluate critical component shortages."}]
            with pytest.raises(AppException) as exc_info:
                await llm_service.chat_completion(messages=messages, provider="openai")

            assert exc_info.value.status_code == 503
            assert exc_info.value.error_code in ("LLM_CREDENTIALS_MISSING", "LLM_SERVICE_UNAVAILABLE")
            assert "not configured" in exc_info.value.message
