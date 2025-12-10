# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import subprocess

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp

from . import constants


class GuarddogCheck(AgentCheck):
    __NAMESPACE__ = "guarddog"

    def __init__(self, name, init_config, instances):
        super(GuarddogCheck, self).__init__(name, init_config, instances)
        self.package_ecosystem = (
            self.instance.get("package_ecosystem").strip().lower() if self.instance.get("package_ecosystem") else None
        )
        self.path = (
            str(self.instance.get("dependency_file_path")).strip()
            if self.instance.get("dependency_file_path")
            else None
        )
        self.guarddog_path = str(init_config.get('guarddog_path')).strip()
        self.check_initializations.append(self.validate_config)

    def get_guarddog_output(self, cmd_with_abs_path) -> subprocess.CompletedProcess:
        try:
            self.log.debug("Running command: %s", cmd_with_abs_path)
            cmd_output_with_abs_path = subprocess.run(cmd_with_abs_path.split(), capture_output=True, text=True)
            return cmd_output_with_abs_path
        except FileNotFoundError as cmd_error:
            err_message = "GuardDog is not found at configured path."
            self.log.error(err_message)
            raise cmd_error

    def get_enriched_event(self, enrichment_details, result) -> dict:
        return {
            "log": result,
            "enrichment_details": enrichment_details,
        }

    def validate_config(self) -> None:
        if not self.path:
            err_message = (
                "Dependency File Path is required for package ecosystem: "
                f"{self.package_ecosystem} to run the GuardDog scan",
            )
            self.log.error(err_message)
            raise ConfigurationError(err_message)

        elif not os.path.exists(self.path):
            err_message = f"Dependency file does not exist at the configured path: {self.path}"
            self.log.error(err_message)
            raise ConfigurationError(err_message)

        elif not os.access(self.path, os.R_OK):
            err_message = f"Dependency file not readable by agent: {self.path}"
            self.log.error(err_message)
            raise ConfigurationError(err_message)

        elif self.guarddog_path == "":
            err_message = "guarddog_path field should not be an empty string"
            self.log.error(err_message)
            raise ConfigurationError(err_message)

    def check(self, _):
        try:
            current_time = get_current_datetime()
            guarddog_command = constants.GUARDDOG_COMMAND.format(
                package_ecosystem=self.package_ecosystem,
                path=self.path,
            )
            cmd_result = self.get_guarddog_output(self.guarddog_path + " " + guarddog_command)
            if cmd_result.returncode != 0:
                cmd_result_err_message = f"GuardDog command failed: {cmd_result.stderr}"
                self.log.error(cmd_result_err_message)
                raise RuntimeError(cmd_result.stderr)

            try:
                results = json.loads(cmd_result.stdout)
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
                self.log.warning("Unable to decode GuardDog output: %s", str(e))
                raise
        except Exception as e:
            err_message = f"Some error occurred during the check operation: {str(e)}"
            self.log.error(err_message)
            raise
