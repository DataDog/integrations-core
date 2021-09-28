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

    These tables are monotonically increasing, so the metrics are computed from the difference
    in values between check runs.
    """

    def __init__(self):
        self._previous_statements = {}

    def compute_derivative_rows(self, rows, metrics, key):
        """
        Compute the first derivative of column-based metrics for a given set of rows. This function
        takes the difference of the previous check run's values and the current check run's values
        to produce a new set of rows whose values represent the total counts in the time elapsed
        between check runs.

        This differs from `AgentCheck.monotonic_count` in that state for the entire row is kept,
        regardless of whether or not the tags used to uniquely identify the row are submitted as
        metric tags. There is also custom logic around stats resets to discard all rows when a
        negative value is found, rather than just the single metric of that row/column.

        This function resets the statement cache so it should only be called once per check run.

        - **rows** (_List[dict]_) - rows from current check run
        - **metrics** (_List[str]_) - the metrics to compute for each row
        - **key** (_callable_) - function for an ID which uniquely identifies a row across runs
        """
        result = []
        new_cache = {}
        metrics = set(metrics)

        rows = _merge_duplicate_rows(rows, metrics, key)
        if len(rows) > 0:
            dropped_metrics = metrics - set(rows[0].keys())
            if dropped_metrics:
                logger.warning(
                    'Some statement metrics are not available from the table: %s', ','.join(m for m in dropped_metrics)
                )

        for row in rows:
            row_key = key(row)
            if row_key in new_cache:
                logger.error(
                    'Unexpected collision in cached query metrics. Dropping existing row, row_key=%s new=%s dropped=%s',
                    row_key,
                    row,
                    new_cache[row_key],
                )

            # Set the row on the new cache to be checked the next run. This should happen for every row, regardless of
            # whether a metric is submitted for the row during this run or not.
            new_cache[row_key] = row

            prev = self._previous_statements.get(row_key)
            if prev is None:
                continue

            metric_columns = metrics & set(row.keys())

            # Take the diff of all metric values between the current row and the previous run's row.
            # There are a couple of edge cases to be aware of:
            #
            # 1. Table truncation or stats reset: Because the table values are always increasing, a negative value
            #    suggests truncation or a stats reset. In this case, the row difference is discarded and the row should.
            #    be tracked from this run forward.
            #
            # 2. No changes since the previous run: There is no need to store metrics of 0, since that is implied by
            #    the absence of metrics. On any given check run, most rows will have no difference so this optimization
            #    avoids having to send a lot of unnecessary metrics.

            diffed_row = {k: row[k] - prev[k] if k in metric_columns else row[k] for k in row.keys()}

            # Check for negative values, but only in the columns used for metrics
            if any(diffed_row[k] < 0 for k in metric_columns):
                # A "break" might be expected here instead of "continue," but there are cases where a subset of rows
                # are removed. To avoid situations where all results are discarded every check run, we err on the side
                # of potentially including truncated rows that exceed previous run counts.
                continue

            # No changes to the query; no metric needed
            if all(diffed_row[k] == 0 for k in metric_columns):
                continue

            result.append(diffed_row)

        self._previous_statements = new_cache

        return result


def _merge_duplicate_rows(rows, metrics, key):
    """
    Given a list of query rows, merge all duplicate rows as determined by the key function into a single row
    with the sum of the stats of all duplicates. This is motivated by database integrations such as postgres
    that can report many instances of a query that are considered the same after the agent normalization.

    - **rows** (_List[dict]_) - rows from current check run
    - **metrics** (_List[str]_) - the metrics to compute for each row
    - **key** (_callable_) - function for an ID which uniquely identifies a query row across runs
    """

    queries_by_key = {}
    for row in rows:
        merged_row = dict(row)

        query_key = key(merged_row)

        if query_key in queries_by_key:
            merged_state = queries_by_key[query_key]
            queries_by_key[query_key] = {
                k: merged_row[k] + merged_state[k] if k in metrics else merged_state[k] for k in merged_state.keys()
            }
        else:
            queries_by_key[query_key] = merged_row

    return list(queries_by_key.values())
