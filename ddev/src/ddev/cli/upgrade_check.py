import atexit
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests
from packaging.version import InvalidVersion, Version

PACKAGE_NAME = 'ddev'


def default_cache_file() -> Path:
    from platformdirs import user_cache_dir

    return Path(user_cache_dir('ddev', appauthor=False)).expanduser() / "upgrade_check.json"


PYPI_URL = "https://pypi.org/pypi/ddev/json"
CHECK_INTERVAL = timedelta(days=7)


def read_last_run(cache_file):
    # Read the last run from the cache file and return a version and a date.
    # Format: {"version": "1.6.0", "date": "2023-04-11T10:56:39.786412"}
    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
            return Version(data["version"]), datetime.fromisoformat(data["date"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError, InvalidVersion, ValueError):
        return None, None


def write_last_run(version, date, cache_file):
    # Records/overwrites the run in the cache file. If the file isn't there, it will be created
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump({"version": str(version), "date": date.isoformat()}, f)


def exit_handler(app, msg):
    return app.display_info(msg, highlight=False)


def upgrade_check(app, version, cache_file=None, pypi_url=PYPI_URL, check_interval=CHECK_INTERVAL):
    if cache_file is None:
        cache_file = default_cache_file()
    current_version = Version(version)
    if current_version.is_devrelease:
        return
    last_version, last_date = read_last_run(cache_file)
    date_now = datetime.now()

    # If cache does not exist or is older than check_interval, fetch from PyPI
    if not last_version or not last_date or (date_now - last_date >= check_interval):
        try:
            resp = requests.get(pypi_url, timeout=5)
            resp.raise_for_status()
            latest_version = Version(resp.json()["info"]["version"])
            write_last_run(latest_version, date_now, cache_file)
            if latest_version > current_version:
                msg = (
                    f'\n\u001b[31mAn upgrade to version {latest_version} is available for {PACKAGE_NAME}. '
                    f'Your current version is {current_version}\u001b[0m'
                )
                atexit.register(exit_handler, app, msg)
        except (requests.RequestException, OSError, json.JSONDecodeError, KeyError, InvalidVersion) as e:
            logging.debug("Upgrade check failed: %s", e)
            # Record the attempt to prevent even if failed
            try:
                version_to_cache = last_version if last_version else current_version
                write_last_run(version_to_cache, date_now, cache_file)
            except OSError:
                pass
    else:
        if last_version > current_version:
            msg = (
                f'\n\u001b[31mAn upgrade to version {last_version} is available for {PACKAGE_NAME}. '
                f'Your current version is {current_version}\u001b[0m'
            )
            atexit.register(exit_handler, app, msg)
