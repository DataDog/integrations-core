# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_api_client.exceptions import ForbiddenException
from datadog_api_client.v1.api.authentication_api import AuthenticationApi
from datadog_api_client.v2 import ApiClient, Configuration

from datadog_checks.base.errors import ConfigurationError

from . import constants
from .errors import log_and_raise_exception


class DatadogAPIError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class InvalidAPIKeyError(DatadogAPIError):
    pass


class DatadogClient:
    def __init__(self, site: str, dd_api_creds: dict, instance_check: object):
        self.dd_api_creds = dd_api_creds
        api_configuration = Configuration(host=constants.API_SITE.format(site), api_key=dd_api_creds)

        self.api_client = ApiClient(api_configuration)
        self.instance_check = instance_check
        self.host = instance_check.hostname
        self.log = instance_check.log

    def validate_datadog_configurations(self) -> None:
        if not self.dd_api_creds:
            err_message = " Datadog API Key or APP Key is missing."
            self.instance_check.ingest_service_check_and_event(
                status=2,
                tags=constants.API_VAL_TAG,
                message=err_message,
                title=constants.API_VAL_TITLE,
                source_type=constants.API_VAL_SOURCE_TYPE,
            )
            log_and_raise_exception(self, err_message, ConfigurationError)
        try:
            auth_api = AuthenticationApi(self.api_client)
            response = auth_api.validate()
            if response.get("valid") is True:
                success_msg = "Connection with datadog is successful."
                self.log.info(f"{constants.INTEGRATION_PREFIX} | HOST={self.host} | MESSAGE={success_msg}")
            else:
                err_message = f"Something went wrong while validating Datadog API key: {response}"
                log_and_raise_exception(self, err_message, InvalidAPIKeyError)
        except ForbiddenException:
            forbidden_msg = "Datadog API key validation failed. Verify the configured API key."
            log_and_raise_exception(self, forbidden_msg, InvalidAPIKeyError)
        except Exception as err:
            err_message = "Error occurred while validating datadog API key."
            self.log.exception(f"{constants.INTEGRATION_PREFIX} | HOST={self.host} | MESSAGE={err_message} | ERROR={err}")
            raise
