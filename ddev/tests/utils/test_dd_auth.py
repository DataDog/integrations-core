# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import sys
import traceback
from unittest.mock import AsyncMock, MagicMock

import pytest

from ddev.utils import dd_auth


@pytest.fixture
def process(monkeypatch):
    process = MagicMock(returncode=0, communicate=AsyncMock())
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


@pytest.mark.parametrize("field", [b"DD_PAT", b"DD_APP_KEY"])
async def test_dd_auth_extracts_only_the_pat_from_piped_output(process, field, monkeypatch):
    monkeypatch.setenv("DD_AUTH_DOMAIN", "another.example")
    monkeypatch.setenv("DD_AUTH_SHELL", "bash")
    monkeypatch.setenv("DD_AUTH_PAT_CACHE_DURATION", "23h")
    process.communicate.return_value = (b"DD_API_KEY=other_secret\n" + field + b"=ddpat_developer\n", b"")

    token = await dd_auth.acquire_datadog_pat("/auth-bin/dd-auth")

    assert token == "ddpat_developer"
    args, kwargs = asyncio.create_subprocess_exec.call_args
    assert args == ("/auth-bin/dd-auth", "--output")
    assert kwargs["stdin"] == asyncio.subprocess.DEVNULL
    assert kwargs["stdout"] == kwargs["stderr"] == asyncio.subprocess.PIPE
    assert {"DD_AUTH_DOMAIN", "DD_AUTH_SHELL", "DD_AUTH_PAT_CACHE_DURATION"}.isdisjoint(kwargs["env"])


@pytest.mark.parametrize("cached_pat", ["ddpat_rejected", "ddpat_new"], ids=["rejected", "already-replaced"])
async def test_dd_auth_bypasses_cache_only_when_it_returns_the_rejected_pat(process, cached_pat):
    process.communicate.side_effect = [
        (f"DD_PAT={cached_pat}\n".encode(), b""),
        (b"DD_PAT=ddpat_new\n", b""),
    ]

    token = await dd_auth.acquire_datadog_pat("/auth-bin/dd-auth", rejected_pat="ddpat_rejected")

    assert token == "ddpat_new"
    commands = [call.args for call in asyncio.create_subprocess_exec.call_args_list]
    assert commands == [("/auth-bin/dd-auth", "--output")] + (
        [("/auth-bin/dd-auth", "--output", "--no-cache")] if cached_pat == "ddpat_rejected" else []
    )


@pytest.mark.parametrize(
    ("exit_code", "stdout", "stderr", "error_type", "message"),
    [
        (0, b"DD_APP_KEY=malformed_secret content", b"", dd_auth.DdAuthError, "malformed PAT output"),
        (
            1,
            b"DD_APP_KEY=ddpat_developer",
            b"OAuth authentication failed: private_url",
            dd_auth.DdAuthLoginError,
            "login required or failed",
        ),
    ],
)
async def test_dd_auth_failures_do_not_expose_process_output(
    process, exit_code, stdout, stderr, error_type, message, caplog
):
    process.returncode = exit_code
    process.communicate.return_value = (stdout, stderr)
    with pytest.raises(error_type, match=message) as caught:
        await dd_auth.acquire_datadog_pat("/auth-bin/dd-auth")

    output = "".join(traceback.format_exception(caught.value)) + caplog.text
    assert all(secret not in output for secret in ("malformed_secret", "ddpat_developer", "private_url"))


@pytest.mark.parametrize("cancel", [False, True], ids=["timeout", "cancelled"])
@pytest.mark.parametrize("rejected_pat", [None, "ddpat_rejected"], ids=["normal", "cache-bypass"])
async def test_dd_auth_kills_and_reaps_unfinished_child(process, monkeypatch, cancel, rejected_pat):
    started = asyncio.Event()
    killed = asyncio.Event()

    async def communicate() -> tuple[bytes, bytes]:
        started.set()
        await killed.wait()
        return b"", b""

    process.communicate.side_effect = communicate
    process.kill.side_effect = killed.set
    if rejected_pat is not None:
        cached = MagicMock(returncode=0, communicate=AsyncMock(return_value=(b"DD_PAT=ddpat_rejected\n", b"")))
        asyncio.create_subprocess_exec.side_effect = [cached, process]
    if not cancel:
        monkeypatch.setattr(dd_auth, "TOKEN_TIMEOUT", 0)
    task = asyncio.create_task(dd_auth.acquire_datadog_pat("/auth-bin/dd-auth", rejected_pat=rejected_pat))
    await started.wait()
    if cancel:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        with pytest.raises(dd_auth.DdAuthTimeoutError, match="timed out"):
            await task
    process.kill.assert_called_once()
    assert process.communicate.await_count == 2
