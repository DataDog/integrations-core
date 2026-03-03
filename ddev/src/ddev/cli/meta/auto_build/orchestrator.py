# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator


class AutoBuildOrchestrator(EventBusOrchestrator):
    def __init__(self, integration: str, endpoint: str):
        super().__init__(logger=logging.getLogger("auto_build_orchestrator"))

    async def on_initialize(self):
        pass

    async def on_finalize(self, exception: Exception | None):
        pass

    async def on_message_received(self, message: BaseMessage):
        pass
