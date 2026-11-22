"""Abstract LLM provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """
    A provider-agnostic LLM interface.

    Every implementation must return a Pydantic-validated object,
    never free text. This constraint is what makes cross-model
    comparisons scientifically meaningful.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable identifier of the underlying model."""

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
    ) -> T:
        """
        Generate a response and validate it against `response_model`.

        Raises:
            LLMResponseError: if the model output cannot be parsed or validated.
        """


class LLMResponseError(RuntimeError):
    """Raised when an LLM response cannot be parsed into the expected model."""