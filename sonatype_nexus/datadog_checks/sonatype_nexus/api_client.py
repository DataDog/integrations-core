# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from base64 import b64encode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from datadog_checks.base import ConfigurationError

from . import constants
from .errors import handle_errors


class SonatypeNexusClient:
    def __init__(self, instance_check):
        self.instance_check = instance_check
        self.log = instance_check.log
        self.session = self.get_requests_retry_session(self)

    @handle_errors
    def call_sonatype_nexus_api(self, url) -> requests.Response:
        try:
            response = self.session.get(
                url,
                timeout=constants.REQUEST_TIMEOUT,
                headers=self.session.headers,
            )
            return response

        except ConfigurationError:
            err_message = (
                "Error occurred while authenticating the Sonatype Nexus credentials. Please check logs for more details."
            )
            self.instance_check.ingest_service_check_and_event(
                status=2,
                tags=constants.AUTH_TAG,
                message=err_message,
                title=constants.AUTH_TITLE,
                source_type=constants.AUTH_SOURCE_TYPE,
            )
            raise

        except Exception as ex:
            self.log.exception(ex)
            raise

    def get_requests_retry_session(
        self,
        retries=constants.RETRY,
        backoff_factor=constants.BACKOFF_FACTOR,
        status_forcelist=constants.STATUS_FORCELIST,
        allowed_methods=constants.ALLOWED_METHODS,
    ):
        """Creates and returns a session object with retry mechanism."""
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=allowed_methods,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        token = b64encode(f"{self.instance_check._username}:{self.instance_check._password}".encode()).decode("ascii")
        headers.update({"Authorization": f"Basic {token}"})
        session.headers.update(headers)
        return session
