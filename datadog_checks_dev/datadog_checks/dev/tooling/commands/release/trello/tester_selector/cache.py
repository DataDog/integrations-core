# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from datetime import datetime
from typing import Optional

from ....console import echo_info


class Cache:
    """
    Cache data that is expensive to compute. Use JSON format.
    """

    def __init__(self, app_dir: str, cache_name: str, expiration: datetime):
        cache_path = os.path.join(app_dir, '.cache')
        self.__path = os.path.join(cache_path, cache_name)
        try:
            os.mkdir(cache_path)
        except FileExistsError:
            pass
        try:
            creation_time = datetime.utcfromtimestamp(os.path.getctime(self.__path))
            if creation_time < expiration:
                echo_info(f'Cache expired. Removing cache {self.__path}')
                os.remove(self.__path)
        except OSError:
            # file does not exist
            pass

    def get_value(self) -> Optional[object]:
        try:
            with open(self.__path) as f:
                echo_info(f'Load from {self.__path}')
                value_json = f.read()
                return json.loads(value_json)
        except FileNotFoundError:
            return None
        except Exception as e:
            raise Exception(f'Invalid cache object in {self.__path} {type(e)}') from e

    def set_value(self, value: object):
        value_json = json.dumps(value)
        stat = None

        try:
            stat = os.stat(self.__path)
        except FileNotFoundError:
            pass

        with open(self.__path, 'w') as f:
            f.write(value_json)
        if stat:
            # restore file dates for cache expiration
            os.utime(self.__path, (stat.st_atime, stat.st_mtime))
