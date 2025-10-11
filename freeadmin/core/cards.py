# -*- coding: utf-8 -*-
"""
cards

Dashboard card management utilities and state storage.

Version:0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import asyncio
import json
import logging
from time import monotonic
from typing import Any, Dict, Iterator, List, Set

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..conf import FreeAdminSettings, current_settings

from .registry import CardEntry, PageRegistry
from .virtual import VirtualContentKey
from .sse.publisher import PublisherService


class CardManager:
    """Maintain card metadata, state and event publishing."""

    def __init__(
        self,
        registry: PageRegistry,
        *,
        redis_url: str | None = None,
        settings: FreeAdminSettings | None = None,
    ) -> None:
        """Initialize the manager with the registry and Redis configuration."""

        self.registry = registry
        self._settings = settings or current_settings()
        self.redis_url = redis_url or self._settings.redis_url
        self._redis: Redis | None = None
        self._last_state: Dict[str, Any] = {}
        self._publishers: List[PublisherService] = []
        self._publisher_tasks: Dict[PublisherService, asyncio.Task[None]] = {}
        self._pending_events: Set[asyncio.Task[Any]] = set()
        self._publishers_started = False
        self.logger = logging.getLogger(__name__)
        self._redis_retry_at: float | None = None
        self._redis_retry_interval = 30.0
        self._redis_skip_logged = False

    def register_card(
        self,
        key: str,
        app: str,
        title: str,
        template: str,
        *,
        icon: str | None = None,
        channel: str | None = None,
        col_class: str = "col-2",
        scripts: List[str] | None = None,
        styles: List[str] | None = None,
    ) -> None:
        """Register card metadata within the underlying registry.

        Args:
            key: Unique identifier of the card.
            app: Application label that groups the card in navigation.
            title: Display title rendered inside the card.
            template: Path to the template that implements the card.
            icon: Optional Bootstrap icon displayed near the title.
            channel: Optional SSE channel for live updates.
            col_class: Bootstrap column classes applied to the dashboard grid.
            scripts: Extra script asset paths required by the card.
            styles: Extra style asset paths required by the card.
        """

        self.registry.register_card(
            key=key,
            app=app,
            title=title,
            template=template,
            icon=icon,
            channel=channel,
            col_class=col_class,
            scripts=scripts,
            styles=styles,
        )

    def get_card(self, key: str) -> CardEntry:
        """Return the registered card entry associated with ``key``."""

        return self.registry.get_card(key)

    def get_card_virtual(self, key: str) -> VirtualContentKey:
        """Return virtual metadata for the registered card ``key``."""

        entry = self.registry.get_card_virtual(key)
        if entry is None:
            raise ValueError(f"Unknown card: {key}")
        return entry

    def iter_cards(self) -> Iterator[CardEntry]:
        """Yield card entries preserved in the registry."""

        yield from self.registry.iter_cards()

    async def publish_event(self, key: str, payload: Any) -> None:
        """Persist the latest state and publish the payload to the card channel."""

        entry = self.get_card(key)
        self._last_state[key] = payload
        if not entry.channel:
            return
        if not self._should_attempt_redis():
            self._log_redis_skip(key)
            return
        message = self._encode_payload(payload)
        try:
            redis = await self._get_redis()
            await redis.publish(entry.channel, message)
        except RedisError as exc:  # pragma: no cover - runtime guard
            self._schedule_redis_retry(key, exc)

    def get_last_state(self, key: str) -> Any:
        """Return the previously published payload for the given card."""

        return self._last_state.get(key)

    def register_publisher(self, publisher: PublisherService) -> None:
        """Register a publisher responsible for streaming updates."""

        if not getattr(publisher, "card_key", None):
            raise ValueError("PublisherService must define a non-empty card_key")
        try:
            self.get_card(publisher.card_key)
        except ValueError as exc:
            raise ValueError(
                f"Card '{publisher.card_key}' must be registered before attaching a publisher"
            ) from exc
        if any(p.card_key == publisher.card_key for p in self._publishers):
            raise ValueError(f"Publisher already registered for card {publisher.card_key}")
        publisher.attach(self)
        self._publishers.append(publisher)

    async def start_publishers(self) -> None:
        """Start all registered publisher services exactly once."""

        if self._publishers_started:
            return
        self._publishers_started = True
        for publisher in self._publishers:
            try:
                initial_state = publisher.get_initial_state()
            except Exception as exc:  # pragma: no cover - defensive runtime logging
                self.logger.warning(
                    "Failed to fetch initial state from %s: %s", publisher.card_key, exc
                )
                initial_state = {}
            if initial_state is not None:
                try:
                    publisher.publish(initial_state)
                except Exception as exc:  # pragma: no cover - runtime guard
                    self.logger.warning(
                        "Failed to publish initial state for %s: %s", publisher.card_key, exc
                    )
            task = asyncio.create_task(self._run_publisher(publisher))
            self._publisher_tasks[publisher] = task
            task.add_done_callback(lambda t, pub=publisher: self._on_publisher_done(pub, t))

    async def shutdown_publishers(self) -> None:
        """Cancel publisher tasks and invoke their shutdown hooks."""

        publishers = list(self._publisher_tasks.keys())
        tasks = [self._publisher_tasks[publisher] for publisher in publishers]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for publisher in publishers:
            await self._call_publisher_shutdown(publisher)
        self._publisher_tasks.clear()
        if self._pending_events:
            pending = list(self._pending_events)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            self._pending_events.clear()
        self._publishers_started = False

    def receive_from_publisher(
        self, publisher: PublisherService, payload: Dict[str, Any]
    ) -> asyncio.Task[Any]:
        """Accept payload from publisher, update cache and propagate events."""

        self._accept_publisher_state(publisher.card_key, payload)
        task = asyncio.create_task(self.publish_event(publisher.card_key, payload))
        self._pending_events.add(task)
        task.add_done_callback(self._pending_events.discard)
        return task

    def _accept_publisher_state(self, key: str, payload: Dict[str, Any]) -> None:
        self._last_state[key] = payload

    async def _call_publisher_shutdown(self, publisher: PublisherService) -> None:
        try:
            await publisher.shutdown()
        except Exception as exc:  # pragma: no cover - defensive runtime logging
            self.logger.warning(
                "Publisher %s failed during shutdown: %s", publisher.card_key, exc
            )

    async def _run_publisher(self, publisher: PublisherService) -> None:
        try:
            await publisher.run()
        except asyncio.CancelledError:  # pragma: no cover - cancellation path
            raise
        except Exception as exc:  # pragma: no cover - runtime guard
            self.logger.exception(
                "Publisher %s terminated with error: %s", publisher.card_key, exc
            )

    def _on_publisher_done(
        self, publisher: PublisherService, task: asyncio.Task[Any]
    ) -> None:
        self._publisher_tasks.pop(publisher, None)
        if task.cancelled():  # pragma: no cover - cancellation path
            return
        exc = task.exception()
        if exc is not None:  # pragma: no cover - runtime logging
            self.logger.warning(
                "Publisher %s stopped unexpectedly: %s", publisher.card_key, exc
            )

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    @staticmethod
    def _encode_payload(payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, (bytes, bytearray)):
            return payload.decode("utf-8", errors="replace")
        try:
            return json.dumps(payload, ensure_ascii=False)
        except TypeError:
            return json.dumps({"payload": str(payload)}, ensure_ascii=False)

    def _should_attempt_redis(self) -> bool:
        """Return ``True`` when Redis operations are permitted after a failure."""

        if self._redis_retry_at is None:
            return True
        if monotonic() >= self._redis_retry_at:
            self._redis_retry_at = None
            self._redis_skip_logged = False
            return True
        return False

    def _log_redis_skip(self, key: str) -> None:
        if self._redis_skip_logged:
            return
        self.logger.warning(
            "Skipping card event publication for %s; Redis is temporarily unavailable.",
            key,
        )
        self._redis_skip_logged = True

    def _schedule_redis_retry(self, key: str, exc: RedisError) -> None:
        self.logger.warning("Failed to publish card event for %s: %s", key, exc)
        self._redis_retry_at = monotonic() + self._redis_retry_interval
        self._redis_skip_logged = False
        self._redis = None


__all__ = ["CardManager"]


# The End

