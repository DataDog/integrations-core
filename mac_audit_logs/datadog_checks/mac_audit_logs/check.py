# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
from datetime import datetime
from typing import List, Tuple
from xml.etree.ElementTree import ParseError

from lxml import etree

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.errors import (
    ConfigurationError,
    ConfigValueError,
)
from datadog_checks.base.utils.time import get_timestamp

from . import constants, utils


class MacAuditLogsCheck(AgentCheck):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "mac_audit_logs"

    def __init__(self, name, init_config, instances):
        super(MacAuditLogsCheck, self).__init__(name, init_config, instances)

        self.monitor = self.instance.get("MONITOR", True)
        self.audit_logs_dir_path = self.instance.get("AUDIT_LOGS_DIR_PATH", "/var/audit")
        self.min_collection_interval = self.instance.get("min_collection_interval")

    def validate_configurations(self) -> None:
        if not constants.MIN_COLLECTION_INTERVAL <= self.min_collection_interval <= constants.MAX_COLLECTION_INTERVAL:
            err_message = (
                f"'min_collection_interval' must be a positive integer in range of {constants.MIN_COLLECTION_INTERVAL}"
                f" to {constants.MAX_COLLECTION_INTERVAL}, got {self.min_collection_interval}."
            )
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            raise ConfigValueError(err_message)

        if not isinstance(self.monitor, bool):
            err_message = (
                f"The provided 'MONITOR' value '{self.monitor}' is not a valid boolean. "
                "Please provide either 'true' or 'false'."
            )
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            raise ConfigurationError(err_message)

    def collect_relevant_files(self, last_record_time: str) -> List[Tuple[datetime, str]]:
        if not os.path.isdir(self.audit_logs_dir_path):
            err_message = (
                f"`{self.audit_logs_dir_path}` directory does not exist. Please ensure BSM auditing is enabled."
            )
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            return []

        relevant_files = []
        for file_name in os.listdir(self.audit_logs_dir_path):
            if file_name == "current":
                continue

            if file_name.count(".") == 1:
                start_time_str, end_time_str = file_name.split(".")

                start_time = utils.time_string_to_datetime_utc(start_time_str)
                last_record_datetime = utils.time_string_to_datetime_utc(last_record_time)

                if end_time_str == "not_terminated":
                    relevant_files.append((start_time, file_name))
                    continue

                if end_time_str == "crash_recovery":
                    if start_time >= utils.time_string_to_datetime_utc(
                        utils.get_utc_timestamp_minus_hours(constants.HOURS_OFFSET)
                    ):
                        relevant_files.append((start_time, file_name))
                    continue

                end_time = utils.time_string_to_datetime_utc(end_time_str)

                # Include all the files which are withing the time interval
                if start_time <= last_record_datetime <= end_time or last_record_datetime < start_time:
                    relevant_files.append((start_time, file_name))
            else:
                err_message = f"File {file_name} does not have the expected file format."
                self.log.error(constants.LOG_TEMPLATE.format(message=err_message))

        relevant_files.sort(key=lambda x: (x[1].endswith('.not_terminated'), x[0]))
        return relevant_files

    def get_previous_iteration_log_cursor(self, previous_cursor) -> Tuple[str, str, str]:
        last_record_time = utils.get_utc_timestamp_minus_hours(constants.HOURS_OFFSET)
        last_record_milli_sec = None
        last_collected_file_name = None

        self.log.debug(constants.LOG_TEMPLATE.format(message=f"Previous Cursor: {previous_cursor}"))  # noqa: G004
        if previous_cursor:
            last_record_time = previous_cursor["record_time"]
            last_record_milli_sec = previous_cursor["record_milli_sec"]
            last_collected_file_name = previous_cursor["file_name"]

        return last_record_time, last_record_milli_sec, last_collected_file_name

    def fetch_audit_logs(self, file_path, time_filter_arg) -> Tuple[str, str]:
        output = error = ""

        auditreduce_command = f"sudo auditreduce -a {time_filter_arg} {file_path}"
        praudit_command = "sudo praudit -xsl"

        try:
            # use TZ=UTC because auditreduce does not translate daylight savings to UTC and always uses standard time
            auditreduce_process = subprocess.Popen(
                auditreduce_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "TZ": "UTC"},
            )
            praudit_process = subprocess.Popen(
                praudit_command,
                shell=True,
                stdin=auditreduce_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            auditreduce_process.stdout.close()

            output, error = praudit_process.communicate()

            return output, error

        except Exception as e:
            err_message = f"Error processing file {file_path}: {e}"
            self.log.exception(constants.LOG_TEMPLATE.format(message=err_message))
        finally:
            message = "Processes auditreduce and praudit have been closed."
            if auditreduce_process.poll() is None:
                auditreduce_process.terminate()
            if praudit_process.poll() is None:
                praudit_process.terminate()
            self.log.info(constants.LOG_TEMPLATE.format(message=message))

    def process_and_ingest_log_entries(self, log_entries, file, timezone_offset, last_record_milli_sec) -> None:
        total_entries = len(log_entries)
        for log_index, log in enumerate(log_entries):
            try:
                if log.strip() in ["<?xml version='1.0' encoding='UTF-8'?>", "<audit>", ""]:
                    continue

                data_xml = etree.fromstring(log)
                time_value = data_xml.get("time")
                milli_sec_value = data_xml.get("msec")

                # This condition is used to reduce the duplicacy of the records.
                # Skip records until not find the last ingested record milli second time value
                if last_record_milli_sec and last_record_milli_sec != milli_sec_value:
                    continue

                # Set the `last_record_milli_sec` None when reach the last ingested record's milli second time value
                # Once set to None skipping logic will be not initiated
                if last_record_milli_sec == milli_sec_value:
                    last_record_milli_sec = None

                datetime_aware = utils.get_datetime_aware(time_value, timezone_offset)

                cursor = {}
                cursor["record_time"] = utils.convert_local_to_utc_timezone_timestamp_str(time_value, timezone_offset)
                cursor["file_name"] = file

                if log_index + 1 == total_entries:
                    # Set `record_milli_sec` to None and `is_file_collection_completed` to True
                    # when reach the last entry of the file. This indicates the successful
                    # execution of the particular file
                    cursor["record_milli_sec"] = None
                    cursor["is_file_collection_completed"] = True
                else:
                    # Set `record_milli_sec` to millisecond  time value of record and
                    # `is_file_collection_completed` to False for remaining entries
                    # This indicates the ongoing execution of the file
                    cursor["record_milli_sec"] = milli_sec_value
                    cursor["is_file_collection_completed"] = False

                data = {}
                data["timestamp"] = get_timestamp(datetime_aware)
                data["message"] = log

                self.send_log(data, cursor=cursor)
            except ParseError as exe:
                err_message = f"Unable to parse the XML response: {exe}"
                self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
                return
            except Exception as exe:
                err_message = f"Something went wrong while monitoring: {exe}"
                self.log.exception(constants.LOG_TEMPLATE.format(message=err_message))
                raise

    def collect_data_from_files(
        self,
        relevant_files,
        previous_cursor,
        last_record_time,
        last_collected_file_name,
        last_record_milli_sec,
        timezone_offset,
    ) -> None:
        for file_index, (_, file) in enumerate(relevant_files):
            file_path = os.path.join(self.audit_logs_dir_path, file)

            if not os.path.exists(file_path):
                message = f"{file_path} is not available. Skipping collection for this file."
                self.log.info(constants.LOG_TEMPLATE.format(message=message))
                continue

            start_time_str, end_time_str = file.split(".")

            # Skip execution of the file if it is not falls within the time range
            if end_time_str not in ["not_terminated", "crash_recovery"] and utils.time_string_to_datetime_utc(
                end_time_str
            ) < utils.time_string_to_datetime_utc(utils.get_utc_timestamp_minus_hours(constants.HOURS_OFFSET)):
                err_message = (
                    f"Skipping the log collection of {file} file as logs are not within the "
                    f"last {constants.HOURS_OFFSET} hours timeframe."
                )
                self.log.info(constants.LOG_TEMPLATE.format(message=err_message))
                continue

            if previous_cursor:
                cursor_file_start_time_str, cursor_file_end_time_str = last_collected_file_name.split(".")
                # If last proccessed file is `not_terminated`, Skip the already processed files
                if (
                    cursor_file_end_time_str == "not_terminated"
                    and previous_cursor["is_file_collection_completed"]
                    and cursor_file_start_time_str == start_time_str
                    and last_record_time == end_time_str
                ):
                    self.log.debug(f"Skipping the collection of {file} file")  # noqa: G004
                    continue

                # Skip the file if it has been already processed
                if (last_collected_file_name == file and previous_cursor["is_file_collection_completed"]) or (
                    end_time_str not in ["not_terminated", "crash_recovery"]
                    and utils.time_string_to_datetime_utc(start_time_str)
                    <= utils.time_string_to_datetime_utc(last_record_time)
                    and utils.time_string_to_datetime_utc(end_time_str)
                    == utils.time_string_to_datetime_utc(last_record_time)
                    and last_collected_file_name != file
                ):
                    self.log.debug(f"Skipping the collection of {file} file")  # noqa: G004
                    continue

            # Prepare time filter argument for auditreduce command. Set `last_record_time` as a value if
            # the first file to be processed otherwise set this to start-time of file
            time_filter_arg = last_record_time if file_index == 0 else start_time_str

            try:
                output, error = self.fetch_audit_logs(file_path, time_filter_arg)

                output_str = output.decode("utf-8", errors="replace")

                if not output_str.strip():
                    err_message = (
                        f"praudit command produced no output. Error: {error.decode('utf-8', errors='replace')}"
                    )
                    self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
                    continue

                log_entries = output_str.strip().split("\n")

                self.process_and_ingest_log_entries(log_entries, file, timezone_offset, last_record_milli_sec)

            except Exception as e:
                err_message = f"Error processing file {file}: {e}"
                self.log.exception(constants.LOG_TEMPLATE.format(message=err_message))

    def check(self, _):
        try:
            self.validate_configurations()
            message = "All the provided configurations in conf.yaml are valid."
            self.log.info(constants.LOG_TEMPLATE.format(message=message))
        except Exception:
            err_message = (
                "Error occurred while validating the provided configurations in conf.yaml."
                " Please check logs for more details."
            )
            self.log.info(constants.LOG_TEMPLATE.format(message=err_message))
            raise

        if self.monitor:
            previous_cursor = self.get_log_cursor()
            last_record_time, last_record_milli_sec, last_collected_file_name = self.get_previous_iteration_log_cursor(
                previous_cursor
            )

            timezone_offset = subprocess.run(["date", "+%z"], capture_output=True, text=True).stdout.strip()

            # Collect all the files from `audit_logs_dir_path` path which falls under the time range
            relevant_files = self.collect_relevant_files(last_record_time)

            if (
                relevant_files
                and previous_cursor
                and not previous_cursor["is_file_collection_completed"]
                and relevant_files[-1][1] == last_collected_file_name
            ):
                relevant_files = [relevant_files[-1]]
                self.log.debug(
                    f"Found the same file as the last failed iteration, relevant files: {relevant_files}"  # noqa: G004
                )

            self.collect_data_from_files(
                relevant_files,
                previous_cursor,
                last_record_time,
                last_collected_file_name,
                last_record_milli_sec,
                timezone_offset,
            )
        else:
            message = "Monitoring to the Mac Audit Logs is disabled."
            self.log.info(constants.LOG_TEMPLATE.format(message=message))
