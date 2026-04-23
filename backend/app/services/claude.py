from __future__ import annotations

from typing import Any

import structlog
from anthropic import AsyncAnthropic

from app.config import Settings

log = structlog.get_logger()


class ClaudeClient:
    """
    Innpakning av Anthropic SDK for alle LLM-steg i pipelinen.

    Brukes via FastAPI dependency injection — ikke som singleton.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    async def tool_call(
        self,
        system: str,
        user: str,
        tool: dict[str, Any],
        tool_name: str,
        model: str | None = None,
    ) -> Any:
        """
        Kaller Claude med tvungen tool use og returnerer tool-input-dicten.

        Alltid temperature=0 for reproduserbarhet.
        model: overstyrer instansens modell for dette kallet (brukes av lag 3 for Sonnet).
        """
        effective_model = model or self._model
        log.info(
            "claude_tool_call",
            model=effective_model,
            tool=tool_name,
            user_chars=len(user),
        )
        message = await self._client.messages.create(
            model=effective_model,
            max_tokens=4096,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],  # type: ignore[list-item]
            tool_choice={"type": "tool", "name": tool_name},
        )
        log.info(
            "claude_tool_call_ok",
            model=effective_model,
            tool=tool_name,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
        for block in message.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input
        raise RuntimeError(
            f"Ingen '{tool_name}' tool-call i respons fra Claude: {message}"
        )
