# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

logger = logging.getLogger(__name__)


class StatementMetrics:
    """
    This class supports normalized statement-level metrics, which are collected from the database's
    statistics tables, ex:

        - Postgres: pg_stat_statements
        - MySQL: performance_schema.events_statements_summary_by_digest
        - Oracle: V$SQLAREA
        - SQL Server: sys.dm_exec_query_stats
        - DB2: mon_db_summary

    These tables are monotonically increasing.
    """

    def __init__(self):
        self.previous_statements = {}

    def compute_derivative_rows(self, rows, metrics, key):
        """
        Compute the first derivative of column-based metrics for a given set of rows. This also resets the
        statement cache so should only be called once per check run.

        - **rows** (_List[dict]_) - rows from current check run
        - **metrics** (_List[str]_) - the metrics to compute for each row
        - **key** (_callable_) - function for an ID which uniquely identifies a row across runs
        """
        result = []
        new_cache = {}
        negative_result_found = False
        metrics = set(metrics)
        if len(rows) > 0:
            dropped_metrics = metrics - set(rows[0].keys())
            if dropped_metrics:
                logger.warning(
                    'Some statement metrics are not available from the table: %s', ','.join(m for m in dropped_metrics)
                )

        for row in rows:
            row_key = key(row)
            if row_key in new_cache:
                logger.debug(
                    'Collision in cached query metrics. Dropping existing row, row_key=%s new=%s dropped=%s',
                    row_key,
                    row,
                    new_cache[row_key],
                )
            new_cache[row_key] = row
            prev = self.previous_statements.get(row_key)
            if prev is None:
                continue
            metric_columns = metrics & set(row.keys())
            if any([row[k] - prev[k] < 0 for k in metric_columns]):
                # The table was truncated or stats reset; begin tracking again from this point
                negative_result_found = True
                continue
            if all([row[k] - prev[k] == 0 for k in metric_columns]):
                # No metrics to report; query did not run
                continue
            derived = {k: row[k] - prev[k] if k in metric_columns else row[k] for k in row.keys()}
            result.append(derived)

        self.previous_statements = new_cache
        if negative_result_found:
            return []
        return result


def apply_row_limits(rows, metric_limits, tiebreaker_metric, tiebreaker_reverse, key):
    """
    Given a list of query rows, apply limits ensuring that the top k and bottom k of each metric (columns)
    are present. To increase the overlap of rows across metics with the same values (such as 0), the tiebreaker metric
    is used as a second sort dimension.

    - **rows** (_List[dict]_) - rows with columns as metrics
    - **metric_limits** (_Dict[str,Tuple[int,int]]_) - dict of the top k and bottom k limits for each metric
            ex:
            >>> metrics = {
            >>>     'count': (200, 50),
            >>>     'time': (200, 100),
            >>>     'lock_time': (50, 50),
            >>>     ...
            >>>     'rows_sent': (100, 0),
            >>> }
    - **tiebreaker_metric** (_str_) - metric used to resolve ties, intended to increase row overlap in different metrics
    - **tiebreaker_reverse** (_bool_) - whether the tiebreaker metric should be in reverse order (descending)
    - **key** (_callable_) - function for an ID which uniquely identifies a row
    """
    if len(rows) == 0:
        return rows

    limited = dict()
    available_cols = set(rows[0].keys())

    for metric, (top_k, bottom_k) in metric_limits.items():
        if metric not in available_cols:
            continue
        # sort_key uses a secondary sort dimension so that if there are a lot of
        # the same values (like 0), then there will be more overlap in selected rows
        # over time
        if tiebreaker_reverse:

            def sort_key(row):
                return (row[metric], -row[tiebreaker_metric])

        else:

            def sort_key(row):
                return (row[metric], row[tiebreaker_metric])

        sorted_rows = sorted(rows, key=sort_key)

        top = sorted_rows[len(sorted_rows) - top_k :]
        bottom = sorted_rows[:bottom_k]
        for row in top:
            limited[key(row)] = row
        for row in bottom:
            limited[key(row)] = row

    return list(limited.values())
