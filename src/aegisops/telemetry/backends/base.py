"""Abstract base for telemetry backend clients."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx


class BackendClient(ABC):
    """Common interface for all backend clients."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @abstractmethod
    def health(self) -> bool:
        """Return True if the backend is reachable and ready."""