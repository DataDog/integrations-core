from datetime import datetime, timedelta, timezone

from . import constants


def get_utc_timestamp_minus_18_hours() -> str:
    current_utc_time = datetime.now(timezone.utc)
    time_18_hours_ago = current_utc_time - timedelta(hours=18)
    return time_18_hours_ago.strftime("%Y%m%d%H%M%S")


def time_string_to_datetime_utc(time_string) -> datetime:
    return datetime.strptime(time_string, constants.FILE_TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)


def _parse_timezone_offset(tz_offset: str) -> timedelta:
    sign = 1 if tz_offset[0] == "+" else -1
    hours = int(tz_offset[1:3])
    minutes = int(tz_offset[3:5])
    return timedelta(hours=hours, minutes=minutes) * sign


def convert_utc_to_local_timezone_timestamp_str(utc_time: str, tz_offset: str) -> str:
    utc_dt = datetime.strptime(utc_time, constants.FILE_TIMESTAMP_FORMAT)
    offset = _parse_timezone_offset(tz_offset)
    local_dt = utc_dt + offset
    return local_dt.strftime(constants.FILE_TIMESTAMP_FORMAT)


def get_datetime_aware(date_str: str, tz_offset: str) -> datetime:
    dt = datetime.strptime(date_str, constants.TIMESTAMP_FORMAT)
    offset = _parse_timezone_offset(tz_offset)
    return dt.replace(tzinfo=timezone(offset))


def convert_local_to_utc_timezone_timestamp_str(time_string: str, tz_offset: str) -> str:
    local_dt = datetime.strptime(time_string, "%a %b %d %H:%M:%S %Y")
    offset = _parse_timezone_offset(tz_offset)
    utc_dt = local_dt - offset

    return utc_dt.strftime("%Y%m%d%H%M%S")
