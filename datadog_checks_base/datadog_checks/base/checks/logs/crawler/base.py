# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterable

from datadog_checks.base import AgentCheck

if TYPE_CHECKING:
    from datadog_checks.base.checks.logs.crawler.stream import LogStream


class LogCrawlerCheck(AgentCheck, ABC):
    @abstractmethod
    def get_log_streams(self) -> Iterable[LogStream]:
        """
        Yields the log streams associated with this check.
        """

    def process_streams(self) -> None:
        """
        Process the log streams and send the collected logs.

        Crawler checks that need more functionality can implement the `check` method and call this directly.
        """
        for stream in self.get_log_streams():
            last_cursor = self.get_log_cursor(stream.name)
            for record in stream.records(cursor=last_cursor):
                self.send_log(record.data, cursor=record.cursor, stream=stream.name)

    def check(self, _) -> None:
        self.process_streams()
