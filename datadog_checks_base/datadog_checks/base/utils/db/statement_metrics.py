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
        - SQL Server: sys.dm_exec_query_stats

    These tables are monotonically increasing, so the metrics are computed from the difference
    in values between check runs.
    """

    def __init__(self):
        self._previous_statements = {}

    def compute_derivative_rows(self, rows, metrics, key, execution_indicators=None):
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

        :params rows (_List[dict]_): rows from current check run
        :params metrics (_List[str]_): the metrics to compute for each row
        :params key (_callable_): function for an ID which uniquely identifies a row across runs
        :params execution_indicators (_List[str]_): list of metrics that must change to consider a query as executed.
            These are typically metrics that increment only when a query actually executes, such as:
            - PostgreSQL: 'calls' from pg_stat_statements
            - MySQL: 'exec_count' from performance_schema.events_statements_summary_by_digest
            - SQL Server: 'execution_count' from sys.dm_exec_query_stats
            This helps filter out cases where a normalized query was evicted then re-inserted with same call count
            (usually 1) and slight duration change. In this case, the new normalized query entry should be treated
            as the baseline for future diffs.
        :return (_List[dict]_): a list of rows with the first derivative of the metrics
        """
        result = []
        metrics = set(metrics)
        if execution_indicators:
            execution_indicators = set(execution_indicators)

        merged_rows, dropped_metrics = _merge_duplicate_rows(rows, metrics, key)
        if dropped_metrics:
            logger.warning(
                'Some statement metrics are not available from the table: %s', ','.join(m for m in dropped_metrics)
            )

        # Cache metric_columns across rows since rows almost always share the same schema.
        # Recomputed only when a row's keys differ.
        cached_metric_cols = None
        cached_indicator_cols = None

        for row_key, row in merged_rows.items():
            prev = self._previous_statements.get(row_key)
            if prev is None:
                continue

            if cached_metric_cols is not None and cached_metric_cols <= row.keys():
                metric_columns = cached_metric_cols
            else:
                metric_columns = metrics & row.keys() & prev.keys()
                cached_metric_cols = metric_columns
                if execution_indicators:
                    cached_indicator_cols = execution_indicators & metric_columns

            # Check diffs before allocating an output dict: skip rows with
            # negative diffs (stats reset), zero change, or no execution indicator change.
            has_negative = False
            has_change = False
            for k in metric_columns:
                diff = row[k] - prev[k]
                if diff < 0:
                    has_negative = True
                    break
                if diff != 0:
                    has_change = True

            if has_negative or not has_change:
                continue

            if execution_indicators and cached_indicator_cols:
                has_indicator_change = False
                for k in cached_indicator_cols:
                    if row[k] - prev[k] > 0:
                        has_indicator_change = True
                        break
                if not has_indicator_change:
                    continue

            result.append({k: row[k] - prev[k] if k in metric_columns else row[k] for k in row})

        # Update cache in-place: remove stale keys, update existing entries,
        # and only allocate new dicts for rows seen for the first time.
        new_keys = merged_rows.keys()
        stale_keys = self._previous_statements.keys() - new_keys
        for k in stale_keys:
            del self._previous_statements[k]

        for row_key, row in merged_rows.items():
            prev = self._previous_statements.get(row_key)
            if prev is not None:
                # Sync columns to handle schema changes (e.g. DB upgrade, plan timing toggled without restarting the check).
                for col in metrics:
                    if col in row:
                        prev[col] = row[col]
                    elif col in prev:
                        del prev[col]
            else:
                self._previous_statements[row_key] = {col: row[col] for col in metrics if col in row}

        return result


def _merge_duplicate_rows(rows, metrics, key):
    """
    Given a list of query rows, merge all duplicate rows as determined by the key function into a single row
    with the sum of the stats of all duplicates. This is motivated by database integrations such as postgres
    that can report many instances of a query that are considered the same after the agent normalization.

    :param rows (_List[dict]_): rows from current check run
    :param metrics (_List[str]_): the metrics to compute for each row
    :param key (_callable_): function for an ID which uniquely identifies a query row across runs
    :return (_Tuple[Dict[str, dict], Set[str]_): a dictionary of merged rows and a set of dropped metrics
    """
    queries_by_key = {}
    dropped_metrics = set()
    for row in rows:
        query_key = key(row)
        if query_key in queries_by_key:
            for metric in metrics:
                if metric in row:
                    queries_by_key[query_key][metric] = queries_by_key[query_key].get(metric, 0) + row[metric]
                else:
                    dropped_metrics.add(metric)
        else:
            queries_by_key[query_key] = row

    return queries_by_key, dropped_metrics
