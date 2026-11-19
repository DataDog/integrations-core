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


def find_dd_auth() -> str | None:
    """Look up `dd-auth` without searching relative PATH entries."""
    for entry in os.get_exec_path():
        if os.path.isabs(entry):
            # On Windows, a bare command can make shutil.which search the working directory first.
            executable = shutil.which(os.path.join(entry, "dd-auth"))
            if executable is not None:
                return executable
    return None


async def acquire_datadog_pat(executable: str) -> str:
    """Capture a Datadog PAT from `dd-auth --output` using the default domain."""
    env = os.environ.copy()
    env.pop("DD_AUTH_DOMAIN", None)
    env.pop("DD_AUTH_SHELL", None)
    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            "--output",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except OSError:
        raise DdAuthLaunchError("Could not launch dd-auth.") from None

    try:
        async with asyncio.timeout(TOKEN_TIMEOUT):
            stdout, stderr = await process.communicate()
    except (TimeoutError, asyncio.CancelledError) as error:
        with suppress(ProcessLookupError):
            process.kill()
        await process.communicate()
        if isinstance(error, asyncio.CancelledError):
            raise
        raise DdAuthError(f"dd-auth timed out after {TOKEN_TIMEOUT} seconds.") from None

    if process.returncode != 0:
        failure = "dd-auth login required or failed" if b"oauth" in stderr.lower() else "dd-auth failed"
        raise DdAuthError(f"{failure}.")

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
