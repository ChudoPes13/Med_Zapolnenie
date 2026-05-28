from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import get_settings


class LLMUnavailableError(RuntimeError):
    pass


class LlamaServerClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.llama_server_url.rstrip("/")
        self.model = settings.llama_model
        self.timeout = settings.llama_timeout_s

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/models")
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def extract_json(self, transcript: str, current_emk: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Ты локальный медицинский ассистент стоматолога. "
            "Извлеки только факты из русскоязычного диалога в JSON patch для ЭМК 043/у. "
            "Не выдумывай значения. Ключи: complaints, anamnesis, objective, diagnosis, "
            "dental, prescriptions, recommendations, allergy, blood_pressure.\n\n"
            f"Текущая ЭМК JSON:\n{json.dumps(current_emk, ensure_ascii=False)}\n\n"
            f"Новый фрагмент:\n{transcript}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(str(exc)) from exc

        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            message = f"llama-server returned invalid JSON: {content[:200]}"
            raise LLMUnavailableError(message) from exc
