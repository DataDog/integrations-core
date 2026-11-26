# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any


@dataclass(frozen=True)
class Notice:
    """An observation that doesn't require an answer.

    Define concrete notices in `notices.py` next to the code that publishes them.
    """


@dataclass(frozen=True)
class Responder[R]:
    """A question and handler paired by `Question.answered_by()`."""

    kind: type
    handler: Callable[[Any], Awaitable[R]]


@dataclass(frozen=True)
class Question[R]:
    """A request for a decision with answer type `R`.

    Register a responder through the question class's `answered_by()` method.

    Current questions need only one responder. A future `Poll[R]` would call
    responders in sequence with individual timeouts and return one result per
    responder to the asker, at the cost of waiting for each in turn.
    """

    @classmethod
    def answered_by[Q](cls: type[Q], handler: Callable[[Q], Awaitable[R]]) -> Responder[R]:
        """Build the responder registration accepted by `RunEvents.respond()`."""
        return Responder(cls, handler)


@dataclass(frozen=True)
class Answered[R]:
    value: R


class Unanswered(StrEnum):
    NO_RESPONDER = auto()
    TIMED_OUT = auto()
    RESPONDER_FAILED = auto()


@dataclass(frozen=True)
class NotAnswered:
    reason: Unanswered


class RunEvents:
    """Dispatch one run's messages to subscribers of their exact type.

    For background notices, the caller supplies an active `notice_task_group`
    that stays open for the run and outlives each `notify()` call. A group
    opened inside `notify()` would wait for the subscribers before returning.
    """

    def __init__(
        self, *, logger: logging.Logger | None = None, notice_task_group: asyncio.TaskGroup | None = None
    ) -> None:
        self._logger = logger if logger is not None else logging.getLogger(__name__)
        self._notice_task_group = notice_task_group
        self._subscribers: dict[type, list[Callable[[Any], Awaitable[None]]]] = {}
        self._responders: dict[type, Callable[[Any], Awaitable[Any]]] = {}
        self._response_lock = asyncio.Lock()
        self._active_response: object | None = None
        self._response_context: ContextVar[object | None] = ContextVar("response_context", default=None)

    def subscribe[M: Notice | Question[Any]](self, kind: type[M], handler: Callable[[M], Awaitable[None]]) -> None:
        self._subscribers.setdefault(kind, []).append(handler)

    def respond[R](self, responder: Responder[R]) -> None:
        """Register a responder for a question type.

        Example:
            events.respond(GatewayLoginFailed.answered_by(ask_user_to_log_in))

        Registering through the question class lets the type checker verify both
        the handler's question type and its answer type. A second responder for
        the same question type raises `ValueError`.
        """
        if responder.kind in self._responders:
            raise ValueError(f"A responder is already registered for {responder.kind.__name__}")
        self._responders[responder.kind] = responder.handler

    async def notify(self, notice: Notice, *, block: bool = True) -> None:
        """Wait for subscribers in order by default.

        With `block=False`, schedule them on the run's active task group and return.
        Background deliveries have no ordering guarantee, even relative to inline ones.
        """
        if block:
            await self._dispatch(notice)
        elif self._notice_task_group is None:
            raise RuntimeError("Background notices require a run-owned task group")
        else:
            await self._dispatch(notice, tasks=self._notice_task_group)

    async def ask[R](self, question: Question[R], *, timeout: float) -> Answered[R] | NotAnswered:
        """Observe the question, then wait for its responder's turn.

        The timeout covers the response only, not subscribers or waiting for the lock.
        A responder may not ask another question on this pipe while answering.

        Example:
            match await events.ask(question, timeout=30):
                case Answered(value):
                    handle_answer(value)
                case NotAnswered(reason):
                    handle_unanswered(reason)
        """
        if self._active_response is not None and self._response_context.get() is self._active_response:
            raise RuntimeError("A responder cannot ask another question on the same RunEvents")

        await self._dispatch(question)
        kind = type(question)
        responder = self._responders.get(kind)
        if responder is None:
            return NotAnswered(Unanswered.NO_RESPONDER)

        async with self._response_lock:
            self._active_response = object()
            token = self._response_context.set(self._active_response)
            try:
                try:
                    async with asyncio.timeout(timeout) as deadline:
                        value = await responder(question)
                except Exception:
                    if not deadline.expired():
                        self._logger.exception("Responder failed for %s", kind.__name__)
                        return NotAnswered(Unanswered.RESPONDER_FAILED)
                else:
                    if not deadline.expired():
                        return Answered(value)
                return NotAnswered(Unanswered.TIMED_OUT)
            finally:
                self._response_context.reset(token)
                self._active_response = None

    async def _dispatch(self, message: Notice | Question[Any], *, tasks: asyncio.TaskGroup | None = None) -> None:
        for handler in tuple(self._subscribers.get(type(message), ())):
            if tasks is None:
                await self._deliver(handler, message)
            else:
                tasks.create_task(self._deliver(handler, message))

    async def _deliver(self, handler: Callable[[Any], Awaitable[None]], message: Notice | Question[Any]) -> None:
        try:
            await handler(message)
        except Exception:
            self._logger.exception("Subscriber failed for %s", type(message).__name__)
