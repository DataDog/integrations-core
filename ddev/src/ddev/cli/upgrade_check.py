from __future__ import annotations

import atexit
import json
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from ddev.cli.application import Application

PACKAGE_NAME = 'ddev'


def default_cache_file() -> Path:
    from platformdirs import user_cache_dir

    return Path(user_cache_dir('ddev', appauthor=False)).expanduser() / "upgrade_check.json"


PYPI_URL = "https://pypi.org/pypi/ddev/json"
CHECK_INTERVAL = timedelta(days=7)


def read_last_run(cache_file: Path) -> tuple[Version, datetime] | None:
    # Read the last run from the cache file and return a version and a date.
    # Format: {"version": "1.6.0", "date": "2023-04-11T10:56:39.786412"}
    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
            return Version(data["version"]), datetime.fromisoformat(data["date"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError, InvalidVersion, ValueError):
        return None


def write_last_run(version: Version, date: datetime, cache_file: Path):
    # Records/overwrites the run in the cache file. If the file isn't there, it will be created
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump({"version": str(version), "date": date.isoformat()}, f)


def exit_handler(app: Application, latest_version: Version, current_version: Version):
    msg = (
        f'An upgrade to version {latest_version} is available for {PACKAGE_NAME}. '
        f'Your current version is {current_version}'
    )
    app.display_warning(msg, highlight=False)


def upgrade_check(
    app: Application,
    version: str,
    cache_file: Path | None = None,
    pypi_url: str = PYPI_URL,
    check_interval: timedelta = CHECK_INTERVAL,
):
    if cache_file is None:
        cache_file = default_cache_file()
    current_version = Version(version)
    if current_version.is_devrelease:
        return
    last_run = read_last_run(cache_file)
    date_now = datetime.now()

    # If cache does not exist or is older than check_interval, fetch from PyPI
    if last_run is None:
        should_check = True
        last_version = None
    else:
        last_version, last_date = last_run
        should_check = date_now - last_date >= check_interval

    if should_check:
        try:
            resp = requests.get(pypi_url, timeout=5)
            resp.raise_for_status()
            latest_version = Version(resp.json()["info"]["version"])
            write_last_run(latest_version, date_now, cache_file)
            if latest_version > current_version:
                atexit.register(exit_handler, app, latest_version, current_version)
        except (requests.RequestException, OSError, json.JSONDecodeError, KeyError, InvalidVersion) as e:
            app.display_debug(f'Upgrade check failed: {e}')
            # Record the attempt to prevent even if failed
            with suppress(OSError):
                version_to_cache = last_version if last_run is not None else current_version
                write_last_run(version_to_cache, date_now, cache_file)
    else:
        last_version, _last_date = last_run
        if last_version > current_version:
            atexit.register(exit_handler, app, last_version, current_version)
