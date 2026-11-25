# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import logging
import os
import re
import shutil
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass

# Give dd-auth its two-minute OAuth callback timeout plus time to start and shut down.
TOKEN_TIMEOUT = 2 * 60 + 15
# Match the banner from dd-auth's OAuth flow exactly to stop the subprocess early.
# If dd-auth rewords it, the subprocess runs until it exits or times out.
NO_BROWSER_BANNER = b"Could not open browser automatically."
UPGRADE_HELP = "dd-auth v2.0.0 or later is required. Run brew upgrade dd-auth."

logger = logging.getLogger(__name__)


class DdAuthError(Exception):
    """A `dd-auth` failure that does not include subprocess output."""


class DdAuthLaunchError(DdAuthError):
    """The resolved `dd-auth` executable could not be started."""


class DdAuthTimeoutError(DdAuthError):
    """The credential lookup did not complete before the deadline."""


class DdAuthLoginError(DdAuthError):
    """The lookup reported that OAuth login was required or failed."""


class DdAuthNoBrowserError(DdAuthLoginError):
    """dd-auth could not open a browser to complete login."""


class DdAuthCallbackPortsError(DdAuthError):
    """The login callback server could not start on any of its ports."""


class DdAuthMissingPatError(DdAuthError):
    """The command succeeded without emitting a DD_PAT field."""


OAUTH_FAILURES = (
    (
        b"OAuth authentication did not complete within ",
        DdAuthTimeoutError,
        "dd-auth login was not completed before the OAuth timeout.",
    ),
    (b"could not start OAuth callback server:", DdAuthCallbackPortsError, "dd-auth callback ports are unavailable."),
    (b"OAuth authentication failed - check browser for details", DdAuthLoginError, "dd-auth login required or failed."),
)


@dataclass(frozen=True)
class DdAuthLoginPending:
    """The subprocess is running; whether it opened a browser is unknown.

    The event carries no data yet. Progress details can be added without changing the callback signature.
    """


ProgressCallback = Callable[[DdAuthLoginPending], None]


def find_dd_auth() -> str | None:
    """Look up `dd-auth` without searching relative PATH entries."""
    for entry in os.get_exec_path():
        if os.path.isabs(entry):
            # On Windows, a bare command can make shutil.which search the working directory first.
            executable = shutil.which(os.path.join(entry, "dd-auth"))
            if executable is not None:
                return executable
    return None


async def acquire_datadog_pat(
    executable: str, *, rejected_pat: str | None = None, on_progress: ProgressCallback | None = None
) -> str:
    """Capture a PAT for the default domain, bypassing the cache only to replace a rejected PAT.

    The optional callback reports a running child, not whether a browser opened.
    Failures are raised after the child exits or is reaped.
    """
    env = os.environ.copy()
    env.pop("DD_AUTH_DOMAIN", None)
    env.pop("DD_AUTH_SHELL", None)
    # Keep PAT reuse within dd-auth's default 8-hour cache window.
    if env.pop("DD_AUTH_PAT_CACHE_DURATION", None) is not None:
        logger.debug("Ignoring DD_AUTH_PAT_CACHE_DURATION for the dd-auth subprocess.")
    try:
        async with asyncio.timeout(TOKEN_TIMEOUT):
            token = await _run_dd_auth(executable, env, on_progress)
            if token == rejected_pat:
                token = await _run_dd_auth(executable, env, on_progress, "--no-cache")
            return token
    except TimeoutError:
        raise DdAuthTimeoutError(f"dd-auth timed out after {TOKEN_TIMEOUT} seconds.") from None


async def _run_dd_auth(executable: str, env: dict[str, str], on_progress: ProgressCallback | None, *flags: str) -> str:
    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            "--output",
            *flags,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except OSError:
        raise DdAuthLaunchError("Could not launch dd-auth.") from None

    assert process.stdout is not None and process.stderr is not None
    try:
        if on_progress is not None and process.returncode is None:
            on_progress(DdAuthLoginPending())
        # Catch the no-browser banner before exit without letting a full stderr pipe block the child.
        async with asyncio.TaskGroup() as group:
            failure = group.create_task(_read_failure(process.stderr))
            token = await _read_pat(process.stdout)
            if isinstance(token, DdAuthNoBrowserError):
                _kill(process)
                await _drain(process.stdout)
            returncode = await process.wait()
    except BaseException:
        _kill(process)
        await asyncio.gather(_drain(process.stdout), _drain(process.stderr), process.wait())
        raise

    if isinstance(token, DdAuthNoBrowserError):
        raise token
    if returncode != 0:
        raise failure.result() or DdAuthError("dd-auth failed.")
    if isinstance(token, DdAuthError):
        raise token
    return token


def _kill(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        with suppress(ProcessLookupError):
            process.kill()


async def _read_pat(output: asyncio.StreamReader) -> str | DdAuthError:
    token = None
    async for line in _read_lines(output):
        if line == NO_BROWSER_BANNER:
            return DdAuthNoBrowserError("dd-auth could not open a browser.")
        key, separator, value = line.partition(b"=")
        if key == b"DD_PAT" and separator:
            token = value
    if token is None:
        return DdAuthMissingPatError(f"dd-auth did not return DD_PAT. {UPGRADE_HELP}")
    if not re.fullmatch(rb"ddpat_[a-zA-Z0-9_-]+", token):
        return DdAuthError("dd-auth returned malformed PAT output.")
    return token.decode("ascii")


async def _read_failure(output: asyncio.StreamReader) -> DdAuthError | None:
    failure = None
    async for line in _read_lines(output):
        for marker, error_type, message in OAUTH_FAILURES:
            if marker in line:
                failure = error_type(message)
                break
    return failure


async def _read_lines(output: asyncio.StreamReader) -> AsyncIterator[bytes]:
    try:
        async for line in output:
            yield line.rstrip(b"\r\n")
    except ValueError:
        # A line exceeded the pipe reader's limit. Drain without retaining the remainder.
        await _drain(output)


async def _drain(output: asyncio.StreamReader) -> None:
    while await output.read(8192):
        pass
