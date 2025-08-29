from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.db import QueryExecutor
import os
import psycopg2

DEFAULT_COLLECTION_INTERVAL = 10


class PostgresDBMCustomQueries(DBMAsyncJob):
    def __init__(self, check, config, shutdown_callback):
        collection_interval = DEFAULT_COLLECTION_INTERVAL

        self._tags = None
        self.db_pool = check.db_pool
        super().__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=False,
            enabled=True,
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            job_name="dbm-custom-queries",
            shutdown_callback=shutdown_callback,
        )
        self._tags = []
        self._check = check
        self._config = config
        self._log.info(f"STARTING DBM CUSTOM QUERIES: Config: {self._config}")
        self._conn_ttl_ms = self._config.idle_connection_timeout
        self._custom_queries = []
        # map of custom query id to last updated timestamp
        self._last_updated_timestamps = {}
        # map of custom query id to dbname to query executor
        self._query_executors = {}

    def run_job(self):
        self._fetch_custom_queries()
        self._compile_query_executors()
        self._execute_queries()
        self._check.db_pool.prune_connections()

    @property
    def tags(self):
        return self._tags

    @property
    def query_executors(self):
        return self._query_executors

    def _compile_query_executors(self):
        seen_custom_query_ids = set()
        for custom_query in self._custom_queries:
            custom_query_id = custom_query.get('id')
            last_updated_timestamp = custom_query.get('updated_at')
            seen_custom_query_ids.add(custom_query_id)

            # if a custom query is not in our _last_updated_timestamps, we need to build an executor for it.
            if custom_query_id not in self._last_updated_timestamps:
                self._build_query_executor_for_custom_query_object(custom_query)
                self._last_updated_timestamps[custom_query_id] = last_updated_timestamp

            # if a custom query has been updated, we need to update our _last_updated_timestamps
            # and build a new executor for it.

            elif (
                last_updated_timestamp is not None
                and last_updated_timestamp != self._last_updated_timestamps[custom_query_id]
            ):
                self._build_query_executor_for_custom_query_object(custom_query)
                self._last_updated_timestamps[custom_query_id] = last_updated_timestamp

        # remove any custom queries that are no longer in the list of custom queries
        keys_to_remove = []
        for custom_query_id in self._last_updated_timestamps.keys():
            if custom_query_id not in seen_custom_query_ids:
                keys_to_remove.append(custom_query_id)
        for custom_query_id in keys_to_remove:
            del self._last_updated_timestamps[custom_query_id]
            del self._query_executors[custom_query_id]

    def _build_query_executor_for_custom_query_object(self, custom_query):
        self._log.info(
            f"Building query executor for custom query: {custom_query['id']} and name: {custom_query['name']}"
        )
        for dbname in custom_query['databases']:
            if custom_query['id'] not in self._query_executors:
                self._query_executors[custom_query['id']] = {}
            executor = self._build_query_executor(custom_query, dbname)
            executor.compile_queries()
            self._query_executors[custom_query['id']][dbname] = executor

    def _build_query_executor(self, custom_query, dbname):
        configured_query = self._build_configured_query(custom_query)
        return QueryExecutor(
            self._get_raw_query_executor(dbname),  # executor
            self._check,  # submitter
            queries=[configured_query],
            tags=self.tags,
            hostname=self._check.reported_hostname,
            track_operation_time=False,
        )

    def _get_raw_query_executor(self, dbname):
        def execute_query_raw(query):
            return self._execute_query_raw(query, dbname)

        return execute_query_raw

    def _build_configured_query(self, custom_query):
        columns = []

        for column in custom_query['columns_config']:
            if column['type'] == 'tag' and column['tag_key']:
                columns.append(
                    {
                        "name": column['tag_key'],
                        "type": "tag",
                    }
                )
            elif column['type'] == 'metric' and column['metric_name']:
                columns.append(
                    {
                        "name": column['metric_name'],
                        "type": column['metric_type'],
                    }
                )

        return {
            "name": f"custom_query_{custom_query['id']}-{custom_query['name']}",
            "query": custom_query['query'],
            "columns": columns,
            "collection_interval": custom_query['run_interval'],
        }

    def _execute_query_raw(self, query, dbname):
        with self._check.db_pool.get_connection(dbname, self._config.idle_connection_timeout) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query)
                return cursor.fetchall()

    def _fetch_custom_queries(self):
        """
        Makes a POST request to the specified endpoint and prints the output.

        Args:
            url: The endpoint URL to make the POST request to
            data: Optional data to send in the POST request body
        """

        # Get DD_API_KEY from env
        dd_api_key = os.getenv("DD_API_KEY")
        dd_site = os.getenv("DD_SITE")
        self._log.info(f"Fetching custom queries with tags: {self._tags}")
        data = {"scope": self._tags}
        url = f"https://{dd_site}/api/intake/databases/custom-queries/fetch"

        try:
            resp = self._check.http.post(url, json=data, extra_headers={"DD-API-KEY": dd_api_key})
            resp.raise_for_status()
            self._log.info(f"POST request to {url}")
            self._log.info(f"Status Code: {resp.status_code}")
            self._log.info(f"Response: {resp.json()}")

            self._custom_queries = self._build_custom_queries_from_http_response(resp.json().get("data", []))

            if resp.status_code >= 400:
                self._log.error(f"Error: Request failed with status code {resp.status_code}")
        except Exception as e:
            self._log.error(f"Unexpected error: {e}")

    def _build_custom_queries_from_http_response(self, raw_queries):
        queries = []
        for q in raw_queries:
            query = q.get("attributes", {})
            query['id'] = q['id']
            queries.append(query)
        return queries

    def _execute_queries(self):
        for custom_query_id, executors_by_dbname in self._query_executors.items():
            self._log.info(
                f"Executing query: {custom_query_id} across the following databases: {list(executors_by_dbname.keys())}"
            )
            for executor in executors_by_dbname.values():
                executor.execute()
