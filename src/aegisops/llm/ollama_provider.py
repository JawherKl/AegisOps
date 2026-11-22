"""Ollama implementation of the LLM provider interface."""
from __future__ import annotations

import json
from typing import Type, TypeVar

import ollama
from pydantic import BaseModel, ValidationError

from aegisops.llm.base import LLMProvider, LLMResponseError

T = TypeVar("T", bound=BaseModel)


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "qwen2.5:7b", host: str = "http://localhost:11434") -> None:
        self._model = model
        self._client = ollama.Client(host=host)

    @property
    def model_name(self) -> str:
        return f"ollama/{self._model}"

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
    ) -> T:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat(
                model=self._model,
                messages=messages,
                format="json",
                options={"temperature": 0.0},
            )
        except Exception as e:
            raise LLMResponseError(f"Ollama call failed: {e}") from e

        raw = response["message"]["content"]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMResponseError(f"Model returned non-JSON: {raw[:200]}") from e

        try:
            return response_model.model_validate(parsed)
        except ValidationError as e:
            raise LLMResponseError(f"Model output failed schema validation: {e}") from e