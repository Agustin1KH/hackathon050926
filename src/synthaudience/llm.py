"""Thin LLM wrapper with Anthropic + OpenAI backends and a Fake for tests."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable, Protocol

from synthaudience.config import get_settings


class LLMClient(Protocol):
    async def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        json_schema: dict | None = None,
    ) -> str | dict: ...

    async def complete_vision(
        self,
        system: str,
        user: str,
        images: list[bytes],
        model: str | None = None,
    ) -> str: ...


class AnthropicClient:
    """Anthropic backend. Returns a dict if json_schema is provided, else str."""

    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        from anthropic import AsyncAnthropic  # local import keeps test-time imports light

        settings = get_settings()
        self._client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)
        self._default_model = default_model or settings.eval_model

    async def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        json_schema: dict | None = None,
    ) -> str | dict:
        model = model or self._default_model
        prompt_user = user
        if json_schema is not None:
            prompt_user = (
                f"{user}\n\nReturn ONLY a JSON object that conforms to this JSON schema:\n"
                f"{json.dumps(json_schema)}\n\nDo not wrap in markdown fences."
            )

        msg = await self._client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt_user}],
        )
        text = "".join(
            block.text for block in msg.content if getattr(block, "type", None) == "text"
        )
        if json_schema is not None:
            return _extract_json(text)
        return text

    async def complete_vision(
        self,
        system: str,
        user: str,
        images: list[bytes],
        model: str | None = None,
    ) -> str:
        import base64

        model = model or self._default_model
        content: list[dict[str, Any]] = []
        for img in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64.standard_b64encode(img).decode("ascii"),
                    },
                }
            )
        content.append({"type": "text", "text": user})

        msg = await self._client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", None) == "text"
        )


class OpenAIClient:
    """OpenAI backend, used when LLM_PROVIDER=openai."""

    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        from openai import AsyncOpenAI

        settings = get_settings()
        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self._default_model = default_model or "gpt-4o-mini"

    async def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        json_schema: dict | None = None,
    ) -> str | dict:
        model = model or self._default_model
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["messages"][1][
                "content"
            ] += f"\n\nReturn JSON conforming to this schema:\n{json.dumps(json_schema)}"

        resp = await self._client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        if json_schema is not None:
            return _extract_json(text)
        return text

    async def complete_vision(
        self,
        system: str,
        user: str,
        images: list[bytes],
        model: str | None = None,
    ) -> str:
        import base64

        model = model or self._default_model
        content: list[dict[str, Any]] = [{"type": "text", "text": user}]
        for img in images:
            data_url = "data:image/jpeg;base64," + base64.standard_b64encode(img).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": data_url}})

        resp = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        )
        return resp.choices[0].message.content or ""


class FakeLLMClient:
    """In-memory client for tests. Pre-program responses by call order or by predicate."""

    def __init__(
        self,
        responses: list[str | dict] | None = None,
        responder: (
            Callable[[str, str, str | None, dict | None], str | dict | Awaitable[str | dict]] | None
        ) = None,
    ):
        self._responses: list[str | dict] = list(responses or [])
        self._responder = responder
        self.calls: list[dict] = []

    def queue(self, response: str | dict) -> None:
        self._responses.append(response)

    async def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        json_schema: dict | None = None,
    ) -> str | dict:
        self.calls.append(
            {"system": system, "user": user, "model": model, "json_schema": json_schema}
        )
        if self._responder is not None:
            result = self._responder(system, user, model, json_schema)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        if not self._responses:
            raise RuntimeError("FakeLLMClient: no queued responses left")
        return self._responses.pop(0)

    async def complete_vision(
        self,
        system: str,
        user: str,
        images: list[bytes],
        model: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "model": model,
                "n_images": len(images),
                "vision": True,
            }
        )
        if self._responder is not None:
            result = self._responder(system, user, model, None)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result) if not isinstance(result, str) else result
        if not self._responses:
            raise RuntimeError("FakeLLMClient: no queued responses left (vision call)")
        out = self._responses.pop(0)
        return out if isinstance(out, str) else str(out)


def get_llm_client() -> LLMClient:
    """Return the configured client for runtime use."""
    settings = get_settings()
    if settings.llm_provider == "openai":
        return OpenAIClient()
    return AnthropicClient()


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of a model response, tolerating stray fences."""
    text = text.strip()
    if text.startswith("```"):
        # strip a ```json ... ``` fence if present
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    # locate the first { and matching outermost }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in LLM output: {text[:200]}")
    return json.loads(text[start : end + 1])
