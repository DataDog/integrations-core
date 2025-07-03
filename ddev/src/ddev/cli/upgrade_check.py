import atexit
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests
from packaging.version import InvalidVersion, Version

PACKAGE_NAME = 'ddev'
CACHE_FILE = Path.home() / ".cache" / "ddev" / "upgrade_check.json"
PYPI_URL = "https://pypi.org/pypi/ddev/json"
CHECK_INTERVAL = timedelta(days=7)


def read_last_run():
    # Read the last run from the cache file and return a version and a date.
    # Format: {"version": "1.6.0", "date": "2023-04-11T10:56:39.786412"}
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            return Version(data["version"]), datetime.fromisoformat(data["date"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError, InvalidVersion):
        return None, None


def write_last_run(version, date):
    # Records/overwrites the run in the cache file. If the file isn't there, it will be created
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"version": str(version), "date": date.isoformat()}, f)


def exit_handler(app, msg):
    return app.display_info(msg, highlight=False)


def upgrade_check(app, version, cache_file=CACHE_FILE, pypi_url=PYPI_URL, check_interval=CHECK_INTERVAL):
    current_version = Version(version)
    last_version, last_date = read_last_run()
    date_now = datetime.now()

    # If cache does not exist or is older than check_interval, fetch from PyPI
    if not last_version or not last_date or (date_now - last_date >= check_interval):
        try:
            resp = requests.get(pypi_url, timeout=5)
            resp.raise_for_status()
            latest_version = Version(resp.json()["info"]["version"])
            write_last_run(latest_version, date_now)
            if latest_version > current_version:
                msg = (
                    f'\n!!An upgrade to version {latest_version} is available for {PACKAGE_NAME}. '
                    f'Your current version is {current_version}!!'
                )
                atexit.register(exit_handler, app, msg)
        except requests.RequestException as e:
            logging.debug("Upgrade check failed: %s", e)
    else:
        if last_version > current_version:
            msg = (
                f'\n!!An upgrade to version {last_version} is available for {PACKAGE_NAME}. '
                f'Your current version is {current_version}!!'
            )
            atexit.register(exit_handler, app, msg)
