# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable
from typing import Any

import requests

from . import constants


class APIError(Exception):
    default_message = "An unknown API error occurred."

    def __init__(self, message: str = None, response: requests.Response = None):
        self.response = response
        super().__init__(message or self.default_message)


class EmptyResponseError(APIError):
    default_message = "No response object received from the API."


class InvalidAPICredentialsError(APIError):
    default_message = "Invalid API credentials provided."


class InsufficientAPIPermissionError(APIError):
    default_message = "Insufficient permissions for the API request."


def handle_errors(method: Callable) -> Callable:
    def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        try:
            response = method(self, *args, **kwargs)

            if response is None:
                raise EmptyResponseError()

            if response.status_code == 401:
                raise InvalidAPICredentialsError()

            if response.status_code == 403:
                raise InsufficientAPIPermissionError()

            if response.status_code not in constants.SUCCESSFUL_STATUS_CODES:
                raise APIError(
                    message=(
                        f"API request failed. URL: {response.url}. "
                        f"Status code: {response.status_code}. Response: {response.text}"
                    ),
                    response=response,
                )

            return response

        except requests.exceptions.Timeout as ex:
            self.log.error("TimeoutError: Timeout while requesting data from the API.")
            raise APIError("Timeout while requesting data from the API.") from ex

        except requests.exceptions.ConnectionError as ex:
            self.log.error("ConnectionError: Error while connecting to the API.")
            raise APIError("Error while connecting to the API.") from ex

        except requests.exceptions.RequestException as ex:
            self.log.error("RequestError: General request error occurred.")
            raise APIError("General request error occurred.") from ex

        except Exception as ex:
            self.log.error("Unexpected error: %s", ex)
            raise APIError("Unexpected error occurred.") from ex

    return wrapper


def log_and_raise_exception(self, error_message: str, exception_type: type[Exception]) -> None:
    self.log.error("%s | HOST=%s | MESSAGE=%s", constants.INTEGRATION_PREFIX, self.hostname, error_message)
    raise exception_type(error_message)
