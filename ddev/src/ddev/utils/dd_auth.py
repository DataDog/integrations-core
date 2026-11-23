# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import os
import re
import shutil
from contextlib import suppress

TOKEN_TIMEOUT = 30


class DdAuthError(Exception):
    """A `dd-auth` failure that does not include subprocess output."""


class DdAuthLaunchError(DdAuthError):
    """The resolved `dd-auth` executable could not be started."""


class DdAuthTimeoutError(DdAuthError):
    """The credential lookup did not complete before the deadline."""


class DdAuthLoginError(DdAuthError):
    """The lookup reported that OAuth login was required or failed."""


def find_dd_auth() -> str | None:
    """Look up `dd-auth` without searching relative PATH entries."""
    for entry in os.get_exec_path():
        if os.path.isabs(entry):
            # On Windows, a bare command can make shutil.which search the working directory first.
            executable = shutil.which(os.path.join(entry, "dd-auth"))
            if executable is not None:
                return executable
    return None


async def acquire_datadog_pat(executable: str, *, rejected_pat: str | None = None) -> str:
    """Capture a PAT for the default domain, bypassing the cache only to replace a rejected PAT."""
    env = os.environ.copy()
    env.pop("DD_AUTH_DOMAIN", None)
    env.pop("DD_AUTH_SHELL", None)
    # Togo's use window assumes dd-auth's default cache lifetime.
    env.pop("DD_AUTH_PAT_CACHE_DURATION", None)
    try:
        async with asyncio.timeout(TOKEN_TIMEOUT):
            token = await _run_dd_auth(executable, env)
            if token == rejected_pat:
                token = await _run_dd_auth(executable, env, "--no-cache")
            return token
    except TimeoutError:
        raise DdAuthTimeoutError(f"dd-auth timed out after {TOKEN_TIMEOUT} seconds.") from None


async def _run_dd_auth(executable: str, env: dict[str, str], *flags: str) -> str:
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

    try:
        stdout, stderr = await process.communicate()
    except asyncio.CancelledError:
        with suppress(ProcessLookupError):
            process.kill()
        await process.communicate()
        raise

    if process.returncode != 0:
        if b"oauth" in stderr.lower():
            raise DdAuthLoginError("dd-auth login required or failed.")
        raise DdAuthError("dd-auth failed.")

    # v2.0 emits the PAT as DD_APP_KEY; newer versions also emit DD_PAT.
    keys: dict[bytes, bytes] = {}
    for line in stdout.splitlines():
        key, _, value = line.partition(b"=")
        if key in (b"DD_PAT", b"DD_APP_KEY"):
            if key in keys:
                raise DdAuthError("dd-auth returned malformed PAT output.")
            keys[key] = value
    token = keys.get(b"DD_PAT", keys.get(b"DD_APP_KEY", b""))
    if not re.fullmatch(rb"ddpat_[a-zA-Z0-9_-]+", token):
        raise DdAuthError("dd-auth returned malformed PAT output.")
    return token.decode("ascii")
