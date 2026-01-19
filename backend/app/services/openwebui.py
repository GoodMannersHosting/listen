from __future__ import annotations

from typing import Optional

import httpx


class OpenWebUIClient:
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout_s: float = 120.0,
        temperature: float = 0.7,
        max_tokens: int = 65535,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout_s
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def chat_completion(self, model: str, system_prompt: str, user_text: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(self.base_url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        # OpenAI-compatible: choices[0].message.content
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = (choices[0] or {}).get("message") or {}
        return (msg.get("content") or "").strip()

