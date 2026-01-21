from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

import httpx

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str


class LLMClient:
    async def chat(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        raise NotImplementedError


@dataclass
class OpenAIChatClient(LLMClient):
    """Minimal OpenAI Chat Completions client using raw HTTP.

    - Reads API key from env in `app.py`.
    - Supports OpenAI-compatible gateways (LiteLLM, vLLM) via base_url override.
    """

    api_key: str
    model: str
    base_url: str = "https://api.openai.com"
    timeout_s: float = 60.0

    async def chat(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("Missing OpenAI API key.")

        url = self.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(url, headers=headers, json=payload)

        # Helpful errors
        if r.status_code == 401:
            raise RuntimeError("OpenAI auth failed (401). Check OPENAI_API_KEY.")
        if r.status_code == 429:
            raise RuntimeError("Rate limited (429). Slow down or raise quota.")
        if r.status_code >= 400:
            # Try to surface API message
            try:
                err = r.json()
            except Exception:
                err = {"raw": r.text}
            raise RuntimeError(f"OpenAI API error {r.status_code}: {err}")

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Unexpected OpenAI response format: {data}") from e
