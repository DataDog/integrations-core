# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from base64 import b64encode

from .errors import handle_errors

INTEGRATION_PREFIX = "sonatype_nexus"
AUTH_TAG = ["tag:sonatype_nexus_authentication_validation"]
AUTH_TITLE = "Sonatype Nexus Authentication validations"
AUTH_SOURCE_TYPE = INTEGRATION_PREFIX + ".authentication_validation"


class SonatypeNexusClient:
    def __init__(self, instance_check):
        self.instance_check = instance_check
        self.log = instance_check.log
        self.http = instance_check.http
        self._set_auth_header()

    def _set_auth_header(self):
        token = b64encode(f"{self.instance_check._username}:{self.instance_check._password}".encode()).decode("ascii")
        self.http.options["headers"].update(
            {
                "Authorization": f"Basic {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    @handle_errors
    def call_sonatype_nexus_api(self, url):
        try:
            response = self.http.get(url)

            if response.status_code == 200:
                success_msg = "Successfully called the Sonatype Nexus API."
                self.instance_check.ingest_event(
                    status=0,
                    tags=AUTH_TAG,
                    message=success_msg,
                    title=AUTH_TITLE,
                    source_type=AUTH_SOURCE_TYPE,
                )
            if response.status_code == 401:
                err_message = (
                    "Error occurred with provided Sonatype Nexus credentials. Please check logs for more details."
                )
                self.instance_check.ingest_event(
                    status=2,
                    tags=AUTH_TAG,
                    message=err_message,
                    title=AUTH_TITLE,
                    source_type=AUTH_SOURCE_TYPE,
                )
            if response.status_code == 402:
                err_message = "Invalid Sonatype Nexus license, access to the requested resource requires payment."
                self.instance_check.ingest_event(
                    status=2,
                    tags=AUTH_TAG,
                    message=err_message,
                    title=AUTH_TITLE,
                    source_type=AUTH_SOURCE_TYPE,
                )
            elif response.status_code == 403:
                err_message = (
                    "Insufficient permissions to call the Sonatype Nexus API. Please check logs for more details."
                )
                self.instance_check.ingest_event(
                    status=2,
                    tags=AUTH_TAG,
                    message=err_message,
                    title=AUTH_TITLE,
                    source_type=AUTH_SOURCE_TYPE,
                )
            return response

        except Exception as ex:
            self.log.error("Error occurred while calling the Sonatype Nexus API: %s", ex)
