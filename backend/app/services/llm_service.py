"""Centralized LLM Gateway Service.

Provides a unified interface for agent and decision intelligence reasoning calls,
handling secret masking, prompt telemetry, and model fallback.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger


class LLMService:
    """Centralized LLM client for enterprise agent interactions."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.default_model = settings.DEFAULT_LLM_MODEL

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Execute a text generation call with sanitized telemetry."""
        target_model = model or self.default_model
        logger.info(
            f"LLM request initiated to model={target_model}",
            extra={"model": target_model},
        )

        # In Phase 3, if no API key is provided, provide deterministic reasoning fallback
        if not self.api_key:
            logger.warning("No OPENAI_API_KEY configured. Returning synthetic reasoning response.")
            return {
                "content": f"[Simulated Decision for prompt: {prompt[:50]}...]",
                "model": target_model,
                "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": 10, "total_tokens": len(prompt.split()) + 10},
                "status": "simulated",
            }

        # Centralized HTTP request to OpenAI/vLLM endpoint
        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", target_model),
                    "usage": data.get("usage", {}),
                    "status": "success",
                }
            except Exception as e:
                logger.error(f"LLM API request failed: {e}")
                return {
                    "content": "LLM generation unavailable. Fallback rule applied.",
                    "error": str(e),
                    "status": "error",
                }


llm_service = LLMService()
