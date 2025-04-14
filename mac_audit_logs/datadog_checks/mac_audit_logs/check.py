# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import ParseError

from lxml import etree

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.errors import (
    ConfigurationError,
    ConfigValueError,
)
from datadog_checks.base.utils.time import get_timestamp

from . import constants


class MacAuditLogsCheck(AgentCheck):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "mac_audit_logs"

    def __init__(self, name, init_config, instances):
        super(MacAuditLogsCheck, self).__init__(name, init_config, instances)

        self.monitor = self.instance.get("MONITOR", True)
        self.min_collection_interval = self.instance.get("min_collection_interval")

    def validate_configurations(self) -> None:

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

    def get_datetime_aware(self, date_str, tz_offset) -> datetime:
        dt = datetime.strptime(date_str, constants.TIMESTAMP_FORMAT)

        sign = 1 if tz_offset[0] == "+" else -1
        hours_offset = int(tz_offset[1:3])
        minutes_offset = int(tz_offset[3:5])
        offset = timedelta(hours=hours_offset, minutes=minutes_offset) * sign

        return dt.replace(tzinfo=timezone(offset))

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
                timezone_offset = subprocess.run(['date', '+%z'], capture_output=True, text=True).stdout.strip()
                praudit_process = subprocess.Popen(
                    ["praudit", "-xsl", "/dev/auditpipe"], stdout=subprocess.PIPE, text=True
                )

                try:
                    for log in praudit_process.stdout:
                        if log.strip() in ["<?xml version='1.0' encoding='UTF-8'?>", "<audit>"]:
                            continue

                        data_xml = etree.fromstring(log)
                        time_value = data_xml.get("time")
                        datetime_aware = self.get_datetime_aware(time_value, timezone_offset)

                        data = {}
                        data['timestamp'] = get_timestamp(datetime_aware)
                        data['message'] = log

                        self.send_log(data)
                except ParseError as exe:
                    self.log.error(f"Unable to parse the XML response: {exe}")  # noqa: G004
                    return
                except Exception as exe:
                    err_message = f"Something went wrong while monitoring: {exe}"
                    self.log.exception(constants.LOG_TEMPLATE.format(host=self.ip, message=err_message))
                    raise
                finally:
                    praudit_process.stdout.close()
                    praudit_process.wait()
        else:
            message = "Monitoring to the Mac Audit Logs is disabled."
            self.log.info(constants.LOG_TEMPLATE.format(host=self.ip, message=message))
