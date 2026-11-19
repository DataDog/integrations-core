# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any

from datadog_checks.sqlserver.utils import raise_if_cancelled

# The event_file target writes `<filename>_0_<timestamp>.xel` files, a new one at each rollover or session start.
EVENT_FILE_SUFFIX_PATTERN = re.compile(r"_\d+_\d+\.xel$", re.IGNORECASE)

# The newest buffer of a file, where the first run starts instead of replaying the history.
EVENT_FILE_LAST_BUFFER_QUERY = """\
SELECT TOP 1 file_name, file_offset
FROM sys.fn_xe_file_target_read_file(?, NULL, NULL, NULL)
ORDER BY file_offset DESC
"""
# The reads and checkpoints rely on `sys.fn_xe_file_target_read_file` returning rows in (file_name, file_offset) order,
# as it reads the files and their buffers one after the other. The documentation doesn't guarantee it, but
# `ORDER BY file_name, file_offset` could sort every row after the checkpoint before `TOP` applies.
EVENT_FILE_READ_QUERY = """\
SELECT TOP (?) event_data, file_name, file_offset
FROM sys.fn_xe_file_target_read_file(?, NULL, NULL, NULL)
"""
# The events of the file the reading started at and the next ones, before the first checkpoint. The file names end with
# the time they were created at, so the files before it sort first.
EVENT_FILE_READ_FROM_START_FILE_QUERY = """\
SELECT TOP (?) event_data, file_name, file_offset
FROM sys.fn_xe_file_target_read_file(?, NULL, NULL, NULL)
WHERE file_name >= ?
"""
# Reading from a checkpoint returns the events of the buffers after it, in this file and the next ones, including the
# file a restarted session starts.
EVENT_FILE_READ_FROM_CHECKPOINT_QUERY = """\
SELECT TOP (?) event_data, file_name, file_offset
FROM sys.fn_xe_file_target_read_file(?, NULL, ?, ?)
"""
# The oldest file the target still retains, as the files are read oldest first.
EVENT_FILE_OLDEST_FILE_QUERY = """\
SELECT TOP 1 file_name
FROM sys.fn_xe_file_target_read_file(?, NULL, NULL, NULL)
"""
# The error of a read from a checkpoint whose file is gone. Drivers that don't report the error number are covered by
# comparing the checkpoint's file with the oldest file retained.
EVENT_FILE_NOT_FOUND_ERROR_PATTERN = re.compile(r"\b25717\b")
# The start file of a read from the oldest file retained: every file name sorts at or after it, so
# `EVENT_FILE_READ_FROM_START_FILE_QUERY` returns the rows of every file.
ALL_RETAINED_FILES = ""


def event_file_pattern(file_name: str) -> str:
    """
    The path matching every file of the event_file target whose current file is `file_name`, for
    `sys.fn_xe_file_target_read_file`: a wildcard pattern for local files, and the blob name prefix for Azure Blob
    Storage URLs, as on Azure SQL Database and Managed Instance, where wildcards aren't allowed.
    """
    if file_name.lower().startswith("https://"):
        return EVENT_FILE_SUFFIX_PATTERN.sub("", file_name)
    return EVENT_FILE_SUFFIX_PATTERN.sub("*.xel", file_name)


@dataclass
class EventFilePosition:
    """Where the reads of an event_file target are. A session created again with another file gets a new position."""

    # The path of every file of the target, from `event_file_pattern`.
    pattern: str
    # The file and offset of the last buffer read in full. Reads start after it.
    checkpoint: tuple[str, int] | None = None
    # Without a checkpoint, reads start at the start of this file and go on into the files after it: the file the
    # first run found empty, or `ALL_RETAINED_FILES` after the checkpoint's file is gone. It's None until the first
    # run's lookup of the newest buffer succeeds.
    start_file: str | None = None
    # The buffer a read starts with when the previous runs read it in part, as a run reads at most `max_events`
    # events, and the number of its events read.
    partial_buffer: tuple[tuple[str, int], int] | None = None


class EventFileReader:
    """
    Reads the new events of an XE session's event_file target, at most `max_events` per read, keeping its position
    between reads.
    """

    def __init__(
        self, session_name: str, max_events: int, log: logging.LoggerAdapter, cancel_event: threading.Event
    ) -> None:
        self._session_name = session_name
        self._max_events = max_events
        self._log = log
        self._cancel_event = cancel_event
        self._position: EventFilePosition | None = None

    def read(self, cursor: Any, current_file: str) -> tuple[str | None, bool]:
        """
        The new events of the event_file target whose current file is `current_file`, as one XML document, and whether
        it can hold events read before, as a read from the start of a file can. The first run starts at the newest
        buffer of the current file, so it doesn't replay the history, and when that file is empty, the next runs read
        it and the files after it until a checkpoint. When the checkpoint's file is gone, reading starts over at the
        oldest file retained, and when a read from the checkpoint fails otherwise, the next run retries it.
        """
        pattern = event_file_pattern(current_file)
        if self._position is None or self._position.pattern != pattern:
            # A session created again with another file starts over.
            self._position = EventFilePosition(pattern)
        position = self._position
        # A position has a start file once the first run's lookup succeeds, before any checkpoint.
        if position.start_file is None:
            cursor.execute(EVENT_FILE_LAST_BUFFER_QUERY, (current_file,))
            row = cursor.fetchone()
            # Only once the lookup succeeds, so a failed one is retried rather than the history read.
            position.start_file = current_file
            if row:
                position.checkpoint = (row[0], int(row[1]))
                return None, False

        rows = None
        if position.checkpoint is not None:
            limit = self._read_limit(position)
            try:
                cursor.execute(EVENT_FILE_READ_FROM_CHECKPOINT_QUERY, (limit, pattern, *position.checkpoint))
                rows = cursor.fetchall()
            except Exception as e:
                raise_if_cancelled(self._cancel_event)
                if not self._checkpoint_file_gone(cursor, position, e):
                    self._log.warning(
                        "Failed to read %s after %s, retrying at the next run: %s",
                        self._session_name,
                        position.checkpoint,
                        e,
                    )
                    return None, False
                self._log.info(
                    "The file of the %s checkpoint %s is gone, reading from the oldest file retained: %s",
                    self._session_name,
                    position.checkpoint,
                    e,
                )
                # The read starts at another position, where the count of the partial buffer's events read doesn't
                # apply. The events read again are skipped by key.
                position = self._position = EventFilePosition(pattern, start_file=ALL_RETAINED_FILES)
        read_from_file_start = rows is None
        if read_from_file_start:
            limit = self._read_limit(position)
            if current_file == position.start_file:
                cursor.execute(EVENT_FILE_READ_QUERY, (limit, current_file))
            else:
                # The start file rolled over, or the session restarted, before a buffer was read in full, or every file
                # retained is read.
                cursor.execute(EVENT_FILE_READ_FROM_START_FILE_QUERY, (limit, pattern, position.start_file))
            rows = cursor.fetchall()
        new_rows = self._advance_checkpoint(position, rows, limit) if rows else []
        if not new_rows:
            return None, read_from_file_start
        return "<events>{}</events>".format("".join(row[0] for row in new_rows if row[0])), read_from_file_start

    def _read_limit(self, position: EventFilePosition) -> int:
        # The events of the partial buffer read before are read again, and skipped.
        return self._max_events + (position.partial_buffer[1] if position.partial_buffer else 0)

    def _checkpoint_file_gone(self, cursor: Any, position: EventFilePosition, error: Exception) -> bool:
        """
        Whether a read from the checkpoint failed because its file is gone, as after rollovers, rather than for a
        reason the next run can retry.
        """
        if EVENT_FILE_NOT_FOUND_ERROR_PATTERN.search(str(error)):
            return True
        try:
            cursor.execute(EVENT_FILE_OLDEST_FILE_QUERY, (position.pattern,))
            row = cursor.fetchone()
        except Exception as e:
            raise_if_cancelled(self._cancel_event)
            self._log.debug("Failed to read the oldest file of %s: %s", self._session_name, e)
            return False
        # The file names end with the time they were created at, so the files the target removed sort first.
        return row is None or position.checkpoint[0] < row[0]

    def _advance_checkpoint(self, position: EventFilePosition, rows: list, limit: int) -> list:
        """
        The rows of a read to process, at most `max_events` not read before, after the checkpoint moves past them and
        no further. A checkpoint is a whole buffer, so a read stopped within a buffer, by its limit or by `max_events`,
        checkpoints on the buffer before it, and the next read skips the events of that buffer already read.
        """
        buffers = [(row[1], int(row[2])) for row in rows]
        skipped = 0
        if position.partial_buffer is not None:
            partial_buffer, partial_rows = position.partial_buffer
            while skipped < min(partial_rows, len(rows)) and buffers[skipped] == partial_buffer:
                skipped += 1
        # The rows after the first `max_events` new ones are left to the next runs.
        end = min(len(rows), skipped + self._max_events)
        if end == len(rows) < limit:
            # The read reached the end of the files, so its last buffer is complete.
            position.checkpoint = buffers[end - 1]
            position.partial_buffer = None
        else:
            last_buffer_start = buffers.index(buffers[end - 1])
            if last_buffer_start > 0:
                position.checkpoint = buffers[last_buffer_start - 1]
            # Otherwise the whole read is within its first buffer, and the checkpoint stays before it.
            position.partial_buffer = (buffers[end - 1], end - last_buffer_start)
        return rows[skipped:end]
