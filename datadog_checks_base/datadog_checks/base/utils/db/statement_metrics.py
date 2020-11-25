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


def apply_row_limits(rows, metric_limits, tiebreaker_metric, tiebreaker_reverse, key):
    """
    Given a list of query rows, apply limits ensuring that the top K and bottom K of each metric (columns)
    are present. To increase the overlap of rows across metics with the same values (such as 0), the tiebreaker metric
    is used as a second sort dimension.

    The reason for this custom limit function on metrics is to guarantee that metric `top()` functions show the true
    top and true bottom K, even if some limits are applied to drop less interesting queries that fall in the middle.

    Longer Explanation of the Algorithm
    -----------------------------------

    Simply taking the top K and bottom K of all metrics is insufficient. For instance, for K=2 you might have rows
    with values:

        | query               | count      | time        | errors      |
        | --------------------|------------|-------------|-------------|
        | select * from dogs  | 1 (bottom) | 10 (top)    |  1 (top)    |
        | delete from dogs    | 2 (bottom) |  8 (top)    |  0 (top)    |
        | commit              | 3          |  7          |  0 (bottom) |
        | rollback            | 4          |  3          |  0 (bottom) |
        | select now()        | 5 (top)    |  2 (bottom) |  0          |
        | begin               | 6 (top)    |  2 (bottom) |  0          |

    If you only take the top 2 and bottom 2 values of each column and submit those metrics, then each query is
    missing a lot of metrics:

        | query               | count      | time        | errors      |
        | --------------------|------------|-------------|-------------|
        | select * from dogs  | 1          | 10          |  1          |
        | delete from dogs    | 2          |  8          |  0          |
        | commit              |            |             |  0          |
        | rollback            |            |             |  0          |
        | select now()        | 5          |  2          |             |
        | begin               | 6          |  2          |             |

    This is fine for showing only one metric, but if the user copies the query tag to find our more information,
    that query should have all of the metrics because it is an "interesting" query.

    To solve that, you can submit all metrics for all rows with at least on metric submitted, but then the worst-case
    for total cardinality is:

        (top K + bottom K) * metric count

    Note that this only applies to one check run and a completely different set of "tied" metrics can be submitted on
    the next check run. Since a large number of rows will have value '0', a tiebreaker is used to bias the selected
    rows to rows already picked in the top K / bottom K for the tiebreaker.


        | query               | count      | time        | errors      |
        | --------------------|------------|-------------|-------------|
        | select * from dogs  | 1          | 10          |  1          |
        | delete from dogs    | 2          |  8          |  0          |
        | commit              |            |             |             |
        | rollback            |            |             |             |
        | select now()        | 5          |  2          |  0          | <-- biased toward top K count
        | begin               | 6          |  2          |  0          | <-- biased toward top K count

    The queries `commit` and `rollback` were not interesting to keep; they were only selected because they have error
    counts 0 (but so do the other queries). So we use the `count` as a tiebreaker to instead choose queries which are
    interesting because they have higher execution counts.

    - **rows** (_List[dict]_) - rows with columns as metrics
    - **metric_limits** (_Dict[str,Tuple[int,int]]_) - dict of the top k and bottom k limits for each metric
            ex:
            >>> metric_limits = {
            >>>     'count': (200, 50),
            >>>     'time': (200, 100),
            >>>     'lock_time': (50, 50),
            >>>     ...
            >>>     'rows_sent': (100, 0),
            >>> }

            The first item in each tuple guarantees the top K rows will be chosen for this metric. The second item
            guarantees the bottom K rows will also be chosen. Both of these numbers are configurable because you
            may want to keep the top 100 slowest queries, but are only interested in the top 10 fastest queries.
            That configuration would look like:

            >>> metric_limits = {
            >>>     'time': (100, 10),  # Top 100, bottom 10
            >>>     ...
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
