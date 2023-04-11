import atexit
import json
import os
from datetime import datetime, timedelta

import requests
from semver import VersionInfo

PACKAGE_NAME = 'ddev'


def read_last_run(file_path):
    # Read the last run the file registry.json and returns a version and a date.
    # Format: {"version": "1.6.0", "date": "2023-04-11T10:56:39.786412"}
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            version = data.get('version')
            date = data.get('date')
            if version and date:
                return version, datetime.fromisoformat(date)
    except:
        pass
    return "0.0.1", datetime.now() - timedelta(days=7)


def write_last_run(file_path, version_value, date):
    # Records/overwrites the run in the registry.json. If the file isn't there, it will be created
    data = {'version': version_value, 'date': date.isoformat()}
    with open(file_path, 'w') as f:
        json.dump(data, f)


def exit_handler(app, msg):
    return app.display_info(msg, highlight=False)


def check_upgrade(app, version):
    # Finds the current location of the config file to put the registry.json in the same directory
    file_path = app.config_file.path
    dir_path, _file_name = os.path.split(file_path)
    registry_name = 'registry.json'
    registry_file_path = os.path.join(dir_path, registry_name)

    current_version = VersionInfo.parse(version)
    latest_version, last_run = read_last_run(registry_file_path)
    date_now = datetime.now()

    # Check from last run to see if the data inside the registry.json is older than 7 days
    # If the last checked version is newer than current.
    if date_now - last_run < timedelta(days=7) and latest_version < current_version:
        msg = (
            f'\n!!An upgrade to version {latest_version} is available for {PACKAGE_NAME}. '
            f'Your current version is {current_version}!!'
        )
        atexit.register(exit_handler, app, msg)
        return

    url = 'https://pypi.org/pypi/ddev/json'

    # Get latest version from PyPI and check with current version. Record the latest version and date.
    try:
        response = requests.get(url, timeout=2)
        response.raise_for_status()
        data = response.json()
        latest_version = data['info']['version']
        write_last_run(registry_file_path, latest_version, date_now)
        if VersionInfo.parse(latest_version) < current_version:
            msg = (
                f'\n!!An upgrade to version {latest_version} is available for {PACKAGE_NAME}. '
                f'Your current version is {current_version}!!'
            )
            atexit.register(exit_handler, app, msg)
    except:
        return
