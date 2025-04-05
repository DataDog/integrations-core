# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import socket
import subprocess

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.errors import (
    ConfigurationError,
    ConfigValueError,
)

from . import constants


class MacAuditLogsCheck(AgentCheck):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "mac_audit_logs"

    def __init__(self, name, init_config, instances):
        super(MacAuditLogsCheck, self).__init__(name, init_config, instances)

        self.host_address = None
        self.monitor = self.instance.get("MONITOR", True)
        self.ip = self.instance.get("IP", constants.LOCALHOST)
        self.port = self.instance.get("PORT")
        self.min_collection_interval = self.instance.get("min_collection_interval")

    def validate_configurations(self) -> None:
        for field_name in constants.REQUIRED_FIELDS:
            if self.instance.get(field_name) is None:
                err_message = f"'{field_name}' field is required."
                raise ConfigurationError(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))

        if not constants.MIN_COLLECTION_INTERVAL <= self.min_collection_interval <= constants.MAX_COLLECTION_INTERVAL:
            err_message = (
                f"'min_collection_interval' must be a positive integer in range of {constants.MIN_COLLECTION_INTERVAL}"
                f" to {constants.MAX_COLLECTION_INTERVAL}, got {self.min_collection_interval}."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))
            raise ConfigValueError(err_message)

        if not isinstance(self.monitor, bool):
            err_message = (
                f"The provided 'MONITOR' value '{self.monitor}' is not a valid boolean. "
                "Please provide either 'true' or 'false'."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))
            raise ConfigurationError(err_message)

        if self.ip != constants.LOCALHOST and not re.match(
            constants.IPV4_PATTERN,
            self.ip,
        ):
            err_message = (
                "'IP' is not valid."
                " Please provide a valid IP address with ipv4 protocol where the datadog agent is installed."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))
            raise ConfigurationError(err_message)

        try:
            self.port = int(self.port)
        except ValueError:
            err_message = f"Invalid 'PORT': {self.port} is not an integer."
            self.log.error(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))

        if not constants.MIN_PORT <= int(self.port) <= constants.MAX_PORT:
            err_message = (
                f"'PORT' must be a positive integer in range of {constants.MIN_PORT}"
                f" to {constants.MAX_PORT}, got {self.port}."
            )
            self.log.error(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))
            raise ConfigurationError(err_message)

    def check(self, _):
        try:
            self.validate_configurations()
            message = "All the provided configurations in conf.yaml are valid."
            self.log.info(constants.LOG_TEMPLATE.format(host=self.ip, message=message))
        except Exception:
            err_message = (
                "Error occurred while validating the provided configurations in conf.yaml."
                " Please check logs for more details."
            )
            raise

        if self.monitor:
            if not os.path.exists("/dev/auditpipe"):
                message = "/dev/auditpipe is not available. Please ensure auditing is enabled."
                self.log.info(constants.LOG_TEMPLATE.format(host=self.ip, message=message))
            else:
                udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                praudit_process = subprocess.Popen(
                    ["praudit", "-xsl", "/dev/auditpipe"], stdout=subprocess.PIPE, text=True
                )

                try:
                    for log in praudit_process.stdout:
                        if log.strip() in ["<?xml version='1.0' encoding='UTF-8'?>", "<audit>"]:
                            continue
                        udp_sock.sendto(log.encode(), (self.ip, self.port))
                except Exception as exe:
                    err_message = f"Something went wrong while monitoring: {exe}"
                    self.log.exception(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))
                    raise
                finally:
                    udp_sock.close()
                    praudit_process.stdout.close()
                    praudit_process.wait()
        else:
            message = "Monitoring to the Mac Audit Logs is disabled."
            self.log.info(constants.LOG_TEMPLATE.format(host=self.ip, message=message))
