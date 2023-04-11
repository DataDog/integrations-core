import atexit
import json
import os
import requests
from datetime import datetime, timedelta
from semver import VersionInfo

PACKAGE_NAME = 'ddev'

def read_last_run(file_path):
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
    data = {'version': version_value, 'date': date.isoformat()}
    with open(file_path, 'w') as f:
        json.dump(data, f)

def exit_handler(app, msg):
    return app.display_info(msg, highlight=False)   

def check_upgrade(app, version):
    file_path = app.config_file.path
    dir_path, _file_name = os.path.split(file_path)
    registry_name = 'registry.json'
    registry_file_path = os.path.join(dir_path, registry_name)
    current_version = VersionInfo.parse(version)
    last_checked_version, last_run = read_last_run(registry_file_path)
    date_now = datetime.now()
    
    if date_now - last_run < timedelta(days=7) and last_checked_version < current_version:
        msg = f'\n!!An upgrade to version {last_checked_version} is available for {PACKAGE_NAME}. Your current version is {current_version}!!'
        atexit.register(exit_handler, app, msg)
        return
    
    url = 'https://pypi.org/pypi/ddev/json'

    try:
        response = requests.get(url, timeout=2)
        response.raise_for_status()
        data = response.json()
        latest_version = data['info']['version']
        write_last_run(registry_file_path, latest_version, date_now)
        if VersionInfo.parse(latest_version) < current_version:
            msg = f'\n!!An upgrade to version {latest_version} is available for {PACKAGE_NAME}. Your current version is {current_version}!!'
            atexit.register(exit_handler, app, msg)
    except:
        return