# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import bisect
import os
import subprocess
from datetime import datetime
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

    def collect_relevant_files(
        self, last_record_time: str
    ) -> tuple[list[tuple[datetime, datetime, str]], list[tuple[datetime, str]]]:
        if not os.path.isdir(self.audit_logs_dir_path):
            err_message = (
                f"`{self.audit_logs_dir_path}` directory does not exist. Please ensure BSM auditing is enabled."
            )
            self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
            return [], []

        closed: list[tuple[datetime, datetime, str]] = []
        still_open: list[tuple[datetime, str]] = []
        lookback_cutoff = utils.time_string_to_datetime_utc(utils.get_utc_timestamp_minus_hours(constants.HOURS_OFFSET))
        last_record_datetime = utils.time_string_to_datetime_utc(last_record_time)

        for file_name in os.listdir(self.audit_logs_dir_path):
            if file_name == "current":
                continue

            file_path = os.path.join(self.audit_logs_dir_path, file_name)
            if not os.path.isfile(file_path):
                self.log.debug(constants.LOG_TEMPLATE.format(message=f"Skipping non-file entry: {file_name}"))
                continue

            if file_name.count(".") != 1:
                self.log.debug(
                    constants.LOG_TEMPLATE.format(message=f"Skipping file with unexpected format: {file_name}")
                )
                continue

            start_time_str, end_time_str = file_name.split(".")
            start_time = utils.time_string_to_datetime_utc(start_time_str)

            if end_time_str == "not_terminated":
                still_open.append((start_time, file_name))
                continue

            if end_time_str == "crash_recovery":
                if start_time >= lookback_cutoff:
                    still_open.append((start_time, file_name))
                continue

            end_time = utils.time_string_to_datetime_utc(end_time_str)
            if end_time < lookback_cutoff:
                self.log.info(
                    constants.LOG_TEMPLATE.format(
                        message=f"Skipping the log collection of {file_name} file as logs are not within "
                        f"the last {constants.HOURS_OFFSET} hours timeframe."
                    )
                )
                continue
            if start_time <= last_record_datetime <= end_time or last_record_datetime < start_time:
                closed.append((start_time, end_time, file_name))

        closed.sort(key=lambda x: x[0])
        still_open.sort(key=lambda x: x[0])
        return closed, still_open

    def get_previous_iteration_log_cursor(
        self, previous_cursor: dict | None
    ) -> tuple[str, str | None, list[str], list[str]]:
        last_record_time = utils.get_utc_timestamp_minus_hours(constants.HOURS_OFFSET)
        last_record_milli_sec = None
        last_completed_closed: list[str] = []
        last_completed_open: list[str] = []

        self.log.debug(constants.LOG_TEMPLATE.format(message=f"Previous Cursor: {previous_cursor}"))  # noqa: G004
        if previous_cursor:
            last_record_time = previous_cursor["record_time"]
            last_record_milli_sec = previous_cursor["record_milli_sec"]
            last_completed_closed = previous_cursor.get("last_completed_closed", [])
            last_completed_open = previous_cursor.get("last_completed_open", [])

        return last_record_time, last_record_milli_sec, last_completed_closed, last_completed_open

    def fetch_audit_logs(self, file_paths: list[str], time_filter_arg: str) -> tuple[bytes, bytes]:
        output = error = b""
        auditreduce_process = None
        praudit_process = None

        try:
            # use TZ=UTC because auditreduce does not translate daylight savings to UTC and always uses standard time
            auditreduce_process = subprocess.Popen(
                ["sudo", "auditreduce", "-a", time_filter_arg, *file_paths],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "TZ": "UTC"},
            )
            praudit_process = subprocess.Popen(
                ["sudo", "praudit", "-xsl"],
                stdin=auditreduce_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            auditreduce_process.stdout.close()

            output, error = praudit_process.communicate()
        except Exception as e:
            err_message = f"Error processing files {file_paths}: {e}"
            self.log.exception(constants.LOG_TEMPLATE.format(message=err_message))
        finally:
            for proc in (auditreduce_process, praudit_process):
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            self.log.info(constants.LOG_TEMPLATE.format(message="Processes auditreduce and praudit have been closed."))

        return output, error

    def process_and_ingest_log_entries(
        self,
        log_entries: list[str],
        completed_closed: list[str],
        completed_open: list[str],
        timezone_offset: str,
        last_record_milli_sec: str | None,
    ) -> None:
        total_entries = len(log_entries)
        for log_index, log in enumerate(log_entries):
            try:
                if log.strip() in ["<?xml version='1.0' encoding='UTF-8'?>", "<audit>", ""]:
                    continue

                data_xml = etree.fromstring(log)
                time_value = data_xml.get("time")
                milli_sec_value = data_xml.get("msec")

                if last_record_milli_sec is not None:
                    if last_record_milli_sec == milli_sec_value:
                        last_record_milli_sec = None
                    continue

                datetime_aware = utils.get_datetime_aware(time_value, timezone_offset)

                is_last_in_batch = log_index + 1 == total_entries
                cursor = {
                    "record_time": utils.convert_local_to_utc_timezone_timestamp_str(time_value, timezone_offset),
                    "record_milli_sec": None if is_last_in_batch else milli_sec_value,
                    "is_file_collection_completed": is_last_in_batch,
                    "last_completed_closed": completed_closed if is_last_in_batch else [],
                    "last_completed_open": completed_open if is_last_in_batch else [],
                }

                data = {"timestamp": get_timestamp(datetime_aware), "message": log}

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
        closed: list[tuple[datetime, datetime, str]],
        still_open: list[tuple[datetime, str]],
        last_completed_closed: list[str],
        last_completed_open: list[str],
        last_record_time: str,
        last_record_milli_sec: str | None,
        timezone_offset: str,
    ) -> None:
        valid_closed: list[tuple[datetime, datetime, str]] = []
        for start_time, end_time, file_name in closed:
            file_path = os.path.join(self.audit_logs_dir_path, file_name)
            if not os.path.exists(file_path):
                self.log.info(
                    constants.LOG_TEMPLATE.format(
                        message=f"{file_path} is not available. Skipping collection for this file."
                    )
                )
                continue
            if file_name in last_completed_closed:
                self.log.debug(f"Skipping already-collected closed file: {file_name}")  # noqa: G004
                continue
            if _rotated_from_open(start_time, end_time, last_completed_open, last_record_time):
                self.log.debug(f"Skipping file rotated from previously-open file: {file_name}")  # noqa: G004
                continue
            valid_closed.append((start_time, end_time, file_name))

        valid_open: list[tuple[datetime, str]] = []
        for start_time, file_name in still_open:
            file_path = os.path.join(self.audit_logs_dir_path, file_name)
            if not os.path.exists(file_path):
                self.log.info(
                    constants.LOG_TEMPLATE.format(
                        message=f"{file_path} is not available. Skipping collection for this file."
                    )
                )
                continue
            valid_open.append((start_time, file_name))

        valid_paths = [os.path.join(self.audit_logs_dir_path, c[2]) for c in valid_closed] + [
            os.path.join(self.audit_logs_dir_path, o[1]) for o in valid_open
        ]

        if not valid_paths:
            self.log.debug(
                constants.LOG_TEMPLATE.format(
                    message=(
                        f"No files to collect from this cycle "
                        f"(closed candidates: {len(closed)}, open candidates: {len(still_open)})."
                    )
                )
            )
            return

        completed_closed = [c[2] for c in valid_closed]
        completed_open = [o[1] for o in valid_open]

        try:
            output, error = self.fetch_audit_logs(valid_paths, last_record_time)

            output_str = output.decode("utf-8", errors="replace")

            if not output_str.strip():
                err_message = f"praudit command produced no output. Error: {error.decode('utf-8', errors='replace')}"
                self.log.error(constants.LOG_TEMPLATE.format(message=err_message))
                return

            log_entries = output_str.strip().split("\n")

            self.process_and_ingest_log_entries(
                log_entries, completed_closed, completed_open, timezone_offset, last_record_milli_sec
            )

        except Exception as e:
            err_message = f"Error processing files {valid_paths}: {e}"
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
            (
                last_record_time,
                last_record_milli_sec,
                last_completed_closed,
                last_completed_open,
            ) = self.get_previous_iteration_log_cursor(previous_cursor)

            timezone_offset = subprocess.run(["date", "+%z"], capture_output=True, text=True).stdout.strip()

            closed, still_open = self.collect_relevant_files(last_record_time)

            if previous_cursor and not previous_cursor["is_file_collection_completed"]:
                closed, still_open = _narrow_to_resume_tail(
                    closed, still_open, utils.time_string_to_datetime_utc(last_record_time)
                )
                self.log.debug(
                    f"Resuming aborted cycle, narrowed batch: closed={[c[2] for c in closed]}, "  # noqa: G004
                    f"open={[o[1] for o in still_open]}"
                )

            self.collect_data_from_files(
                closed,
                still_open,
                last_completed_closed,
                last_completed_open,
                last_record_time,
                last_record_milli_sec,
                timezone_offset,
            )
        else:
            message = "Monitoring to the Mac Audit Logs is disabled."
            self.log.info(constants.LOG_TEMPLATE.format(message=message))


def _narrow_to_resume_tail(
    closed: list[tuple[datetime, datetime, str]],
    still_open: list[tuple[datetime, str]],
    last_record_datetime: datetime,
) -> tuple[list[tuple[datetime, datetime, str]], list[tuple[datetime, str]]]:
    if closed:
        starts = [c[0] for c in closed]
        i = bisect.bisect_right(starts, last_record_datetime) - 1
        if i >= 0:
            start, end, _ = closed[i]
            if start <= last_record_datetime <= end:
                return closed[i:], still_open
    return [], still_open


def _rotated_from_open(
    start_time: datetime,
    end_time: datetime,
    last_completed_open: list[str],
    last_record_time: str,
) -> bool:
    if end_time != utils.time_string_to_datetime_utc(last_record_time):
        return False
    start_time_str = start_time.strftime(constants.FILE_TIMESTAMP_FORMAT)
    for name in last_completed_open:
        if name.split(".", 1)[0] == start_time_str:
            return True
    return False
