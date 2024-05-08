# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from typing import Callable, List, Optional

from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.core import QueryExecutor
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_MAJOR_VERSION


class SqlserverDatabaseMetricsBase:
    def __init__(
        self,
        instance_config,
        new_query_executor,
        server_static_info,
        execute_query_handler,
        track_operation_time=False,
        databases=None,
    ):
        self.instance_config: dict = instance_config
        self.server_static_info: dict = server_static_info
        self.new_query_executor: Callable[
            [List[dict], Callable, Optional[List[str]], Optional[bool]], QueryExecutor
        ] = new_query_executor
        self.execute_query_handler: Callable[[str, Optional[str]], List[tuple]] = execute_query_handler
        self.track_operation_time: bool = track_operation_time
        self._databases: Optional[List[str]] = databases
        self._query_executors: List[QueryExecutor] = []
        self.log = get_check_logger()

    @property
    def major_version(self) -> Optional[int]:
        return self.server_static_info.get(STATIC_INFO_MAJOR_VERSION)

    @property
    def engine_edition(self) -> Optional[int]:
        return self.server_static_info.get(STATIC_INFO_ENGINE_EDITION)

    @property
    def enabled(self) -> bool:
        raise NotImplementedError

    @property
    def queries(self) -> List[dict]:
        raise NotImplementedError

    @property
    def databases(self) -> Optional[List[str]]:
        return self._databases

    @property
    def query_executors(self) -> List[QueryExecutor]:
        '''
        Returns a list of QueryExecutor objects for the database metrics.
        '''
        if not self._query_executors:
            self._query_executors = self._build_query_executors()
        return self._query_executors

    def _build_query_executors(self) -> List[QueryExecutor]:
        '''
        Builds a list of QueryExecutor objects for the database metrics.
        '''
        executor = self.new_query_executor(
            self.queries, executor=self.execute_query_handler, track_operation_time=self.track_operation_time
        )
        executor.compile_queries()
        return [executor]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"major_version={self.major_version}, "
            f"engine_edition={self.engine_edition})"
        )

    def metric_names(self) -> List[str]:
        '''
        Returns a list of metric names for the queries in the database metrics.
        Note: This method is used for testing purposes in order to verify that the correct metrics are being collected.
        '''
        metric_names = []
        for query in self.queries:
            names = [
                "sqlserver." + c["name"]
                for c in query["columns"]
                if not c["type"].startswith("tag") and c["type"] != "source"
            ]
            if query.get("extras"):
                names.extend(
                    ["sqlserver." + e["name"] for e in query["extras"] if e.get("submit_type") or e.get("type")]
                )
            metric_names.append(names)
        return metric_names

    def tag_names(self) -> List[str]:
        '''
        Returns a list of tag names for the queries in the database metrics.
        Note: This method is used for testing purposes in order to verify that the correct tags are being collected.
        '''
        tag_names = []
        for query in self.queries:
            tag_names.append([c["name"] for c in query["columns"] if c["type"].startswith("tag")])
        return tag_names

    def execute(self) -> None:
        if not self.enabled:
            self.log.debug("%s: not enabled, skipping execution", str(self))
            return
        for query_executor in self.query_executors:
            query_executor.execute()
