# -*- coding: utf-8 -*-
"""
publisher

Base abstractions for card data publishers.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..cards import CardManager


class PublisherService(ABC):
    """Provide the protocol for streaming card state updates."""

    card_key: str

    def __init__(self) -> None:
        """Initialize the publisher with default runtime attributes."""

        self._card_manager: Optional["CardManager"] = None
        self._event_tasks: set[asyncio.Task[Any]] = set()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def attach(self, manager: "CardManager") -> None:
        """Bind this publisher to the given card manager instance."""

        self._card_manager = manager

    def detach(self) -> None:
        """Detach the publisher from the card manager if necessary."""

        self._card_manager = None
        self._cancel_event_tasks()

    def get_initial_state(self) -> Dict[str, Any]:
        """Return the payload that should be sent before the run loop starts."""

        return {}

    def publish(self, payload: Dict[str, Any]) -> None:
        """Forward the payload to the attached card manager."""

        if self._card_manager is None:
            raise RuntimeError("PublisherService must be attached before publishing")
        task = self._card_manager.receive_from_publisher(self, payload)
        if task is not None:
            self._event_tasks.add(task)
            task.add_done_callback(self._event_tasks.discard)

    @abstractmethod
    async def run(self) -> None:
        """Implement the asynchronous loop that produces payloads."""

    async def shutdown(self) -> None:
        """Hook for graceful shutdown of publisher resources."""

        self._cancel_event_tasks()

    def _cancel_event_tasks(self) -> None:
        for task in list(self._event_tasks):
            task.cancel()
        self._event_tasks.clear()


__all__ = ["PublisherService"]


# The End

