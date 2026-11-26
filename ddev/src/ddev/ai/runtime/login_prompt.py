# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

LOGIN_PENDING = "Waiting for the dd-auth login. A browser window may have opened; complete the login there."


@dataclass(frozen=True)
class LoginProblem:
    title: str
    instructions: str


class LoginAction(Enum):
    RETRY = auto()
    CANCEL = auto()


class LoginPrompt(Protocol):
    """Report or resolve login problems without exposing subprocess output."""

    def set_pending(self, pending: bool) -> None: ...

    async def resolve(self, problem: LoginProblem) -> LoginAction: ...


class TerminalLoginPrompt:
    def set_pending(self, pending: bool) -> None:
        if pending:
            print(LOGIN_PENDING, file=sys.stderr)

    async def resolve(self, problem: LoginProblem) -> LoginAction:
        print(problem.instructions, file=sys.stderr)
        return LoginAction.CANCEL
