# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from . import constants


class APIError(Exception):
    message = "Unknown API error occurred."

    def __init__(self, message=message, response=None):
        self.response = response
        super().__init__(message)


class EmptyResponseError(APIError):
    message = "Not received response object from API."

    def __init__(self, message=message):
        super().__init__(message)


class InvalidAPICredentialsError(APIError):
    message = "API Credentials are invalid."

    def __init__(self, message=message):
        super().__init__(message)


class InsufficientAPIPermissionError(APIError):
    message = "API does not have sufficient permissions."

    def __init__(self, message=message):
        super().__init__(message)


def handle_errors(method):
    def wrapper(self, *args, **kwargs):
        err = None
        err_msg = None
        try:
            res = method(self, *args, **kwargs)

            if res is None:
                raise EmptyResponseError

            elif res.status_code == 401:
                raise InvalidAPICredentialsError

            elif res.status_code == 403:
                raise InsufficientAPIPermissionError

            elif res.status_code not in constants.SUCCESSFUL_STATUSCODE:
                raise APIError(
                    f"Request to API server failed. URL: {res.url}."
                    f"Status code: {res.status_code}. Response: {res.text}",
                    res,
                )

            return res

        except requests.exceptions.Timeout as ex:
            err_msg = "TimeoutError: Timeout while requesting data from Platform."
            err = ex

        except requests.exceptions.ConnectionError as ex:
            err_msg = "ConnectionError: Error while connecting."
            err = ex

        except requests.exceptions.RequestException as ex:
            err_msg = "RequestError: Error while fetching data."
            err = ex

        raise APIError(err_msg + f" Error: {err}")

    return wrapper


def log_and_raise_exception(self, error_message: str, exception_type: type[Exception]):
    self.log.error("%s | HOST=%s | MESSAGE=%s", constants.INTEGRATION_PREFIX, self.hostname, error_message)
    raise exception_type(error_message)
