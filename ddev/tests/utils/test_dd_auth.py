# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import logging
import os
import sys
import traceback
from unittest.mock import AsyncMock

import pytest

from ddev.utils import dd_auth


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.returncode: int | None = None
        self.exited = asyncio.Event()
        self.killed = False
        self.reaped = False

    def finish(self, stdout: bytes = b"", stderr: bytes = b"", *, exit_code: int = 0) -> None:
        self.stdout.feed_data(stdout)
        self.stderr.feed_data(stderr)
        self.stdout.feed_eof()
        self.stderr.feed_eof()
        self.returncode = exit_code
        self.exited.set()

    async def wait(self) -> int:
        await self.exited.wait()
        self.reaped = True
        assert self.returncode is not None
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.finish(exit_code=-9)


@pytest.fixture
async def process(monkeypatch: pytest.MonkeyPatch) -> FakeProcess:
    process = FakeProcess()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    return process


def test_dd_auth_lookup_ignores_relative_path_entries(tmp_path, monkeypatch):
    filename = "dd-auth.EXE" if sys.platform == "win32" else "dd-auth"
    (tmp_path / filename).touch(mode=0o700)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", ".")

    assert dd_auth.find_dd_auth() is None


def test_dd_auth_lookup_does_not_implicitly_search_working_directory(tmp_path, monkeypatch):
    filename = "dd-auth.EXE" if sys.platform == "win32" else "dd-auth"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    installed = bin_dir / filename
    installed.touch(mode=0o700)
    (tmp_path / filename).touch(mode=0o700)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(bin_dir))
    if sys.platform == "win32":
        monkeypatch.setenv("PATHEXT", ".EXE")
        monkeypatch.delenv("NoDefaultCurrentDirectoryInExePath", raising=False)

    assert dd_auth.find_dd_auth() == str(installed)


async def test_dd_auth_extracts_only_the_pat_from_piped_output(process, monkeypatch, caplog):
    monkeypatch.setenv("DD_AUTH_DOMAIN", "another.example")
    monkeypatch.setenv("DD_AUTH_SHELL", "bash")
    monkeypatch.setenv("DD_AUTH_PAT_CACHE_DURATION", "custom-cache-duration")
    process.finish(b"DD_API_KEY=other_secret\nDD_PAT=ddpat_developer\n")

    with caplog.at_level(logging.DEBUG, logger=dd_auth.__name__):
        token = await dd_auth.acquire_datadog_pat("/auth-bin/dd-auth")

    assert token == "ddpat_developer"
    args, kwargs = asyncio.create_subprocess_exec.call_args
    assert args == ("/auth-bin/dd-auth", "--output")
    assert kwargs["stdin"] == asyncio.subprocess.DEVNULL
    assert kwargs["stdout"] == kwargs["stderr"] == asyncio.subprocess.PIPE
    assert {"DD_AUTH_DOMAIN", "DD_AUTH_SHELL", "DD_AUTH_PAT_CACHE_DURATION"}.isdisjoint(kwargs["env"])
    assert os.environ["DD_AUTH_PAT_CACHE_DURATION"] == "custom-cache-duration"
    assert "Ignoring DD_AUTH_PAT_CACHE_DURATION" in caplog.text
    assert "custom-cache-duration" not in caplog.text


@pytest.mark.parametrize("cached_pat", ["ddpat_rejected", "ddpat_new"], ids=["rejected", "already-replaced"])
async def test_dd_auth_bypasses_cache_only_when_it_returns_the_rejected_pat(process, cached_pat):
    process.finish(f"DD_PAT={cached_pat}\n".encode())
    replacement = FakeProcess()
    replacement.finish(b"DD_PAT=ddpat_new\n")
    asyncio.create_subprocess_exec.side_effect = [process, replacement]

    token = await dd_auth.acquire_datadog_pat("/auth-bin/dd-auth", rejected_pat="ddpat_rejected")

    assert token == "ddpat_new"
    commands = [call.args for call in asyncio.create_subprocess_exec.call_args_list]
    assert commands == [("/auth-bin/dd-auth", "--output")] + (
        [("/auth-bin/dd-auth", "--output", "--no-cache")] if cached_pat == "ddpat_rejected" else []
    )


@pytest.mark.parametrize(
    ("exit_code", "stdout", "stderr", "error_type", "message"),
    [
        (0, b"DD_PAT=malformed_secret content", b"", dd_auth.DdAuthError, "malformed PAT output"),
        (0, b"DD_APP_KEY=ddpat_developer", b"", dd_auth.DdAuthMissingPatError, "Run brew upgrade dd-auth"),
        (
            1,
            b"DD_PAT=ddpat_developer",
            b'{"level":"fatal","msg":"OAuth authentication failed - check browser for details","detail":"private_url"}',
            dd_auth.DdAuthLoginError,
            "login required or failed",
        ),
        (
            1,
            b"DD_PAT=ddpat_developer",
            b'{"level":"fatal","msg":"OAuth authentication did not complete within 2m0s","detail":"private_url"}',
            dd_auth.DdAuthTimeoutError,
            "login was not completed",
        ),
        (
            1,
            b"DD_PAT=ddpat_developer",
            b'{"level":"fatal","msg":"could not start OAuth callback server: private_url\\n'
            b'Is another software listening on all the following ports: [8123 8291 8314 8464 8725 8907]?"}',
            dd_auth.DdAuthCallbackPortsError,
            "callback ports are unavailable",
        ),
        (1, b"DD_PAT=ddpat_developer", b"OAuth: private_url", dd_auth.DdAuthError, r"^dd-auth failed\.$"),
    ],
)
async def test_dd_auth_failures_do_not_expose_process_output(
    process, exit_code, stdout, stderr, error_type, message, caplog
):
    process.finish(stdout, stderr, exit_code=exit_code)
    with pytest.raises(error_type, match=message) as caught:
        await dd_auth.acquire_datadog_pat("/auth-bin/dd-auth")

    output = "".join(traceback.format_exception(caught.value)) + caplog.text
    assert all(secret not in output for secret in ("malformed_secret", "ddpat_developer", "private_url"))


async def test_dd_auth_reaps_child_when_browser_cannot_open(process, caplog):
    pending = asyncio.Event()
    events: list[dd_auth.DdAuthLoginPending] = []

    def on_progress(event: dd_auth.DdAuthLoginPending) -> None:
        events.append(event)
        pending.set()

    async with asyncio.timeout(2):
        task = asyncio.create_task(dd_auth.acquire_datadog_pat("/auth-bin/dd-auth", on_progress=on_progress))
        await pending.wait()
        process.stdout.feed_data(b"DD_API_KEY=other_secret\nCould not open browser automatically.\n")
        process.stdout.feed_data(
            b"Please open the following URL in your browser to authenticate:\n\n"
            b"https://app.datadoghq.com/account/login?next=private_login_url\n\n"
        )
        with pytest.raises(dd_auth.DdAuthNoBrowserError) as caught:
            await task

    assert process.killed and process.reaped
    assert events == [dd_auth.DdAuthLoginPending()]
    output = repr(events) + "".join(traceback.format_exception(caught.value)) + caplog.text
    assert "private_login_url" not in output
    assert "other_secret" not in output


@pytest.mark.parametrize("cancel", [False, True], ids=["timeout", "cancelled"])
@pytest.mark.parametrize("rejected_pat", [None, "ddpat_rejected"], ids=["normal", "cache-bypass"])
async def test_dd_auth_kills_and_reaps_unfinished_child(process, monkeypatch, cancel, rejected_pat):
    if rejected_pat is not None:
        cached = FakeProcess()
        cached.finish(b"DD_PAT=ddpat_rejected\n")
        asyncio.create_subprocess_exec.side_effect = [cached, process]

    timeout = asyncio.timeout
    deadline = timeout(None)
    if not cancel:
        monkeypatch.setattr(asyncio, "timeout", lambda _: deadline)

    pending = asyncio.Event()
    async with timeout(2):
        task = asyncio.create_task(
            dd_auth.acquire_datadog_pat(
                "/auth-bin/dd-auth", rejected_pat=rejected_pat, on_progress=lambda _: pending.set()
            )
        )
        await pending.wait()
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            deadline.reschedule(asyncio.get_running_loop().time())
            with pytest.raises(dd_auth.DdAuthTimeoutError, match="timed out"):
                await task

    assert process.killed and process.reaped
