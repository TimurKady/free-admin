# -*- coding: utf-8 -*-
"""Background publisher feeding demo cards."""

from __future__ import annotations

import asyncio
import random
from typing import Dict

from freeadmin.core.interface.sse.publisher import PublisherService


class TemperaturePublisher(PublisherService):
    """Publish random temperature samples for the demo card."""

    card_key = "thermo1"

    def __init__(self, *, interval: float = 1.0) -> None:
        """Store timing configuration for the demo publisher."""

        super().__init__()
        self.interval = interval

    def get_initial_state(self) -> Dict[str, float]:
        """Provide the baseline temperature before live updates."""

        return {"temp": 25.0}

    async def run(self) -> None:
        """Emit random temperature readings at the configured interval."""

        while True:
            sample = random.uniform(25.0, 40.0)
            self.publish({"temp": round(sample, 2)})
            await asyncio.sleep(self.interval)


__all__ = ["TemperaturePublisher"]

# The End

