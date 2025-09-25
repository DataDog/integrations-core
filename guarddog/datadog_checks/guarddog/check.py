# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import subprocess
from datetime import datetime, timezone

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_timestamp

from . import constants


class GuarddogCheck(AgentCheck):
    __NAMESPACE__ = "guarddog"

    def __init__(self, name, init_config, instances):
        super(GuarddogCheck, self).__init__(name, init_config, instances)
        self.package_ecosystem = (
            self.instance.get("package_ecosystem").strip().lower() if self.instance.get("package_ecosystem") else None
        )
        self.path = (
            self.instance.get("dependency_file_path").strip() if self.instance.get("dependency_file_path") else None
        )

    def get_guarddog_output(self, cmd) -> (str, str, int):
        self.log.debug(cmd)
        res = subprocess.run(cmd.split(), capture_output=True, text=True)
        return res.stdout, res.stderr, res.returncode

    def get_enriched_event(self, enrichment_details, result) -> dict:
        return {
            "log": result,
            "enrichment_details": enrichment_details,
        }

    def validate_config(self) -> None:
        if self.package_ecosystem not in constants.VALID_ECOSYSTEMS:
            err_message = f"Invalid Package Ecosystem provided: {self.package_ecosystem}"
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            raise ConfigurationError(err_message)

        elif not self.path:
            err_message = (
                "Dependency File Path is required for package ecosystem: "
                f"{self.package_ecosystem} to run the guarddog scan",
            )
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            raise ConfigurationError(err_message)

        elif not os.path.exists(self.path):
            err_message = f"Dependency file does not exist at the configured path: {self.path}"
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            raise ConfigurationError(err_message)

        elif not os.access(self.path, os.R_OK):
            err_message = f"Dependency file not readable by agent: {self.path}"
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            raise ConfigurationError(err_message)

    def check(self, _):
        try:
            current_time = datetime.now(tz=timezone.utc)
            self.validate_config()

            guarddog_command = constants.GUARDDOG_COMMAND.format(
                package_ecosystem=self.package_ecosystem, path=self.path
            )
            stdout, stderr, returncode = self.get_guarddog_output(guarddog_command)
            if returncode != 0:
                err_message = f"Guarddog command failed: {stderr}"
                self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
                raise RuntimeError(err_message)

            try:
                results = json.loads(stdout)
                for result in results:
                    triggered_rules = [
                        key for key, value in result.get("result", {}).get("results", {}).items() if value
                    ]
                    enrichment_details = {
                        "triggered_rules": triggered_rules,
                        "package_ecosystem": self.package_ecosystem,
                    }
                    event = self.get_enriched_event(enrichment_details, result)
                    data = {"timestamp": get_timestamp(current_time), "message": json.dumps(event)}
                    self.send_log(data)
            except json.JSONDecodeError as e:
                self.log.warning("Unable to decode guarddog output: %s", str(e))
                raise
        except Exception as e:
            err_message = f"Some error occurred during the check operation: {str(e)}"
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            raise
