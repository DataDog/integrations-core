# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.widgets import Static

from ddev.ai.runtime.login_prompt import LOGIN_PENDING, LoginAction, LoginProblem
from ddev.cli.meta.ai.tui.screens.credential_refresh_modal import LoginRecoveryModal

if TYPE_CHECKING:
    from ddev.cli.meta.ai.tui.app import TogoApp


class LoginPendingNotice(Static):
    def __init__(self) -> None:
        super().__init__(LOGIN_PENDING, id="gateway-login-notice", markup=False)
        self.display = False

    def on_mount(self) -> None:
        self.watch(self.app, "gateway_login_pending", self._set_pending)

    def _set_pending(self, pending: bool) -> None:
        self.display = pending


class TuiLoginPrompt:
    def __init__(self, app: TogoApp) -> None:
        self._app = app

    def set_pending(self, pending: bool) -> None:
        self._app.gateway_login_pending = pending

    async def resolve(self, problem: LoginProblem) -> LoginAction:
        modal = LoginRecoveryModal(problem)
        answer: asyncio.Future[LoginAction] = asyncio.get_running_loop().create_future()

        def reply(action: LoginAction | None) -> None:
            if not answer.done():
                answer.set_result(action or LoginAction.CANCEL)

        self._app.push_screen(modal, reply)
        try:
            return await answer
        finally:
            if modal.is_current:
                modal.dismiss(LoginAction.CANCEL)
