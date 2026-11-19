# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from functools import wraps

from datadog_checks.base.utils.http_exceptions import HTTPClientError


def handle_error(f):
    @wraps(f)
    def wrapper(check, *args, **kwargs):
        try:
            result = f(check, *args, **kwargs)
            return result
        # requests raised JSON decoding errors as a RequestException; the layer raises them outside its tree.
        except (HTTPClientError, json.JSONDecodeError) as e:
            check.log.debug(
                "Encountered a RequestException in '%s' [%s]: %s",
                f.__name__,
                type(e),
                e,
            )
        except Exception as e:
            check.log.error(
                "Encountered an Exception in '%s' [%s]: %s",
                f.__name__,
                type(e),
                e,
            )
        return None

    return wrapper
