# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import HTTPError


def http_error(message):
    def decorator_func(func):
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except HTTPError as e:
                self.log.error("%s: %s", message, e)

        return wrapper

    return decorator_func
