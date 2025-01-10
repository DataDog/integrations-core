# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from base64 import b64encode

import requests

from . import constants
from .errors import handle_errors


class SonatypeNexusClient:
    def __init__(self, instance_check):
        self.instance_check = instance_check
        self.log = instance_check.log
        self.session = self.prepare_session()

    @handle_errors
    def call_sonatype_nexus_api(self, url) -> requests.Response:
        max_retries = 3
        retry_wait = 2

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=constants.REQUEST_TIMEOUT,
                    headers=self.session.headers,
                )

                if response.status_code == 200:
                    success_msg = "Successfully called the Sonatype Nexus API."
                    self.instance_check.ingest_service_check_and_event(
                        status=0,
                        tags=constants.AUTH_TAG,
                        message=success_msg,
                        title=constants.AUTH_TITLE,
                        source_type=constants.AUTH_SOURCE_TYPE,
                    )
                if response.status_code == 401:
                    err_message = (
                        "Error occurred while calling the Sonatype Nexus credentials. "
                        "Please check logs for more details."
                    )
                    self.instance_check.ingest_service_check_and_event(
                        status=2,
                        tags=constants.AUTH_TAG,
                        message=err_message,
                        title=constants.AUTH_TITLE,
                        source_type=constants.AUTH_SOURCE_TYPE,
                    )
                elif response.status_code == 403:
                    err_message = (
                        "Insufficient permissions to call the Sonatype Nexus API. "
                        "Please check logs for more details."
                    )
                    self.instance_check.ingest_service_check_and_event(
                        status=2,
                        tags=constants.AUTH_TAG,
                        message=err_message,
                        title=constants.AUTH_TITLE,
                        source_type=constants.AUTH_SOURCE_TYPE,
                    )

                response.raise_for_status()
                return response

            except Exception as ex:
                self.log.error("Error occurred while calling the Sonatype Nexus API: %s", ex)
                wait_time = retry_wait * (2**attempt)  # Exponential backoff
                self.log.warning(f"Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)

        raise RuntimeError("Max retries exceeded")

    def prepare_session(self):
        """Creates and returns a session object with retry mechanism."""
        session = requests.Session()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        token = b64encode(f"{self.instance_check._username}:{self.instance_check._password}".encode()).decode("ascii")
        headers.update({"Authorization": f"Basic {token}"})
        session.headers.update(headers)
        return session
