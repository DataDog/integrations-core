# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.callbacks.protocols.phase import OnPhaseFinishCallback, OnPhaseStartCallback
from ddev.ai.callbacks.protocols.react import (
    AfterCompactCallback,
    BeforeCompactCallback,
    OnAgentResponseCallback,
    OnBeforeAgentSendCallback,
    OnCompleteCallback,
    OnErrorCallback,
    OnToolCallCallback,
)
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult


class CallbackSet:
    """Decorator-based registry for framework lifecycle event handlers.

    Group related handlers in a single instance for semantic cohesion, then
    compose multiple instances via Callbacks():

        class Logger(CallbackSet):
            def __init__(self):
                super().__init__()

                @self.on_complete
                async def log_done(result: ReActResult) -> None:
                    print(f"Done in {result.iterations} iterations")

        callbacks = Callbacks([Logger(), MetricsEmitter()])
    """

    def __init__(self) -> None:
        self._on_agent_response: list[OnAgentResponseCallback] = []
        self._on_tool_call: list[OnToolCallCallback] = []
        self._on_complete: list[OnCompleteCallback] = []
        self._on_error: list[OnErrorCallback] = []
        self._before_compact: list[BeforeCompactCallback] = []
        self._after_compact: list[AfterCompactCallback] = []
        self._on_before_agent_send: list[OnBeforeAgentSendCallback] = []
        self._on_phase_start: list[OnPhaseStartCallback] = []
        self._on_phase_finish: list[OnPhaseFinishCallback] = []

    def on_agent_response(self, func: OnAgentResponseCallback) -> OnAgentResponseCallback:
        self._on_agent_response.append(func)
        return func

    async def fire_agent_response(self, response: AgentResponse, iteration: int) -> None:
        for handler in self._on_agent_response:
            try:
                await handler(response, iteration)
            except Exception:
                pass

    def on_tool_call(self, func: OnToolCallCallback) -> OnToolCallCallback:
        self._on_tool_call.append(func)
        return func

    async def fire_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        for handler in self._on_tool_call:
            try:
                await handler(tool_call, result, iteration)
            except Exception:
                pass

    def on_complete(self, func: OnCompleteCallback) -> OnCompleteCallback:
        self._on_complete.append(func)
        return func

    async def fire_complete(self, result: ReActResult) -> None:
        for handler in self._on_complete:
            try:
                await handler(result)
            except Exception:
                pass

    def on_error(self, func: OnErrorCallback) -> OnErrorCallback:
        self._on_error.append(func)
        return func

    async def fire_error(self, error: BaseException) -> None:
        for handler in self._on_error:
            try:
                await handler(error)
            except Exception:
                pass

    def on_before_compact(self, func: BeforeCompactCallback) -> BeforeCompactCallback:
        self._before_compact.append(func)
        return func

    async def fire_before_compact(self) -> None:
        for handler in self._before_compact:
            try:
                await handler()
            except Exception:
                pass

    def on_after_compact(self, func: AfterCompactCallback) -> AfterCompactCallback:
        self._after_compact.append(func)
        return func

    async def fire_after_compact(self) -> None:
        for handler in self._after_compact:
            try:
                await handler()
            except Exception:
                pass

    def on_before_agent_send(self, func: OnBeforeAgentSendCallback) -> OnBeforeAgentSendCallback:
        self._on_before_agent_send.append(func)
        return func

    async def fire_before_agent_send(self, iteration: int) -> None:
        for handler in self._on_before_agent_send:
            try:
                await handler(iteration)
            except Exception:
                pass

    def on_phase_start(self, func: OnPhaseStartCallback) -> OnPhaseStartCallback:
        self._on_phase_start.append(func)
        return func

    async def fire_phase_start(self, phase_id: str) -> None:
        for handler in self._on_phase_start:
            try:
                await handler(phase_id)
            except Exception:
                pass

    def on_phase_finish(self, func: OnPhaseFinishCallback) -> OnPhaseFinishCallback:
        self._on_phase_finish.append(func)
        return func

    async def fire_phase_finish(self, phase_id: str) -> None:
        for handler in self._on_phase_finish:
            try:
                await handler(phase_id)
            except Exception:
                pass


class Callbacks:
    """Container of CallbackSet instances. Dispatches each fire_* to all contained sets.

    Usage::

        callbacks = Callbacks([Logger(), MetricsEmitter()])
        process = ReActProcess(agent, registry, callbacks=callbacks)
    """

    def __init__(self, sets: list[CallbackSet] | None = None) -> None:
        self._sets: list[CallbackSet] = sets or []

    async def fire_agent_response(self, response: AgentResponse, iteration: int) -> None:
        for s in self._sets:
            await s.fire_agent_response(response, iteration)

    async def fire_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        for s in self._sets:
            await s.fire_tool_call(tool_call, result, iteration)

    async def fire_complete(self, result: ReActResult) -> None:
        for s in self._sets:
            await s.fire_complete(result)

    async def fire_error(self, error: BaseException) -> None:
        for s in self._sets:
            await s.fire_error(error)

    async def fire_before_compact(self) -> None:
        for s in self._sets:
            await s.fire_before_compact()

    async def fire_after_compact(self) -> None:
        for s in self._sets:
            await s.fire_after_compact()

    async def fire_before_agent_send(self, iteration: int) -> None:
        for s in self._sets:
            await s.fire_before_agent_send(iteration)

    async def fire_phase_start(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_start(phase_id)

    async def fire_phase_finish(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_finish(phase_id)
