# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable
from typing import Any

import requests


class APIError(Exception):
    default_message = "An unknown API error occurred."

    def __init__(self, message: str = None, response: requests.Response = None):
        self.response = response
        super().__init__(message or self.default_message)


class EmptyResponseError(APIError):
    default_message = "No response object received from the API."


class InvalidAPICredentialsError(APIError):
    default_message = "Error occurred with provided Sonatype Nexus credentials."


class InsufficientAPIPermissionError(APIError):
    default_message = "Insufficient permissions to call the Sonatype Nexus API."


class LicenseExpiredError(APIError):
    default_message = "Invalid Sonatype Nexus license, access to the requested resource requires payment."


class BadRequestError(APIError):
    default_message = "Bad request error occurred when calling the Sonatype Nexus API."


class NotFoundError(APIError):
    default_message = "Resource not found while calling the Sonatype Nexus API."


class ServerError(APIError):
    default_message = "Server Error occurred while calling the Sonatype Nexus API."


ERROR_TYPES = {
    400: BadRequestError,
    401: InvalidAPICredentialsError,
    402: LicenseExpiredError,
    403: InsufficientAPIPermissionError,
    404: NotFoundError,
}


SUCCESSFUL_STATUS_CODES = list(range(200, 299))


def handle_errors(method: Callable) -> Callable:
    def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        try:
            response = method(self, *args, **kwargs)

            if response is None:
                raise EmptyResponseError()

            if response.status_code in [400, 401, 402, 403, 404]:
                raise ERROR_TYPES[response.status_code]()

            if response.status_code in [500, 502, 503, 504]:
                raise ServerError()

            if response.status_code not in SUCCESSFUL_STATUS_CODES:
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

        except InvalidAPICredentialsError as ex:
            self.log.error("InvalidAPICredentialsError: %s", ex)
            raise InvalidAPICredentialsError() from ex

        except InsufficientAPIPermissionError as ex:
            self.log.error("InsufficientAPIPermissionError: %s", ex)
            raise InsufficientAPIPermissionError() from ex

        except LicenseExpiredError as ex:
            self.log.error("LicenseExpiredError: %s", ex)
            raise LicenseExpiredError() from ex

        except BadRequestError as ex:
            self.log.error("BadRequestError: %s", ex)
            raise BadRequestError() from ex

        except NotFoundError as ex:
            self.log.error("NotFoundError: %s", ex)
            raise NotFoundError() from ex

        except ServerError as ex:
            self.log.error("ServerError: %s", ex)
            raise ServerError() from ex

        except Exception as ex:
            self.log.error("Unexpected error: %s", ex)
            raise APIError("Unexpected error occurred.") from ex

    return wrapper
