# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
from simplejson import JSONDecodeError

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .constants import (
    APPLICATION_STATES,
    COUNT,
    DEPRECATED_MASTER_ADDRESS,
    GAUGE,
    MASTER_ADDRESS,
    MESOS_MASTER_APP_PATH,
    MESOS_SERVICE_CHECK,
    MONOTONIC_COUNT,
    SPARK_APPS_PATH,
    SPARK_CLUSTER_MODE,
    SPARK_DRIVER_METRICS,
    SPARK_DRIVER_MODE,
    SPARK_DRIVER_SERVICE_CHECK,
    SPARK_EXECUTOR_LEVEL_METRICS,
    SPARK_EXECUTOR_METRICS,
    SPARK_JOB_METRICS,
    SPARK_MASTER_APP_PATH,
    SPARK_MASTER_STATE_PATH,
    SPARK_MESOS_MODE,
    SPARK_PRE_20_MODE,
    SPARK_RDD_METRICS,
    SPARK_SERVICE_CHECK,
    SPARK_STAGE_METRICS,
    SPARK_STANDALONE_MODE,
    SPARK_STANDALONE_SERVICE_CHECK,
    SPARK_STREAMING_STATISTICS_METRICS,
    SPARK_STRUCTURED_STREAMING_METRICS,
    SPARK_VERSION_PATH,
    SPARK_YARN_MODE,
    STRUCTURED_STREAMS_METRICS_REGEX,
    UUID_REGEX,
    YARN_APPLICATION_TYPES,
    YARN_APPS_PATH,
    YARN_SERVICE_CHECK,
)


class SparkCheck(AgentCheck):
    HTTP_CONFIG_REMAPPER = {
        'ssl_verify': {'name': 'tls_verify'},
        'ssl_cert': {'name': 'tls_cert'},
        'ssl_ca_cert': {'name': 'tls_ca_cert'},
        'ssl_key': {'name': 'tls_private_key'},
    }

    def __init__(self, name, init_config, instances):
        super(SparkCheck, self).__init__(name, init_config, instances)

        # Spark proxy may display an html warning page, which redirects to the same url with the additional
        # `proxyapproved=true` GET param.
        # The page also sets a cookie that needs to be stored (no need to set persist_connections in the config)
        self.proxy_redirect_cookies = None
        self.tags = self.instance.get('tags', [])
        self.cluster_mode = self.instance.get(SPARK_CLUSTER_MODE)
        if self.cluster_mode is None:
            self.log.warning(
                'The value for `spark_cluster_mode` was not set in the configuration. Defaulting to "%s"',
                SPARK_YARN_MODE,
            )
            self.cluster_mode = SPARK_YARN_MODE
        self._disable_legacy_cluster_tag = is_affirmative(self.instance.get('disable_legacy_cluster_tag', False))
        self.metricsservlet_path = self.instance.get('metricsservlet_path', '/metrics/json')

        self._enable_query_name_tag = is_affirmative(self.instance.get('enable_query_name_tag', False))
        self._disable_spark_job_stage_tags = is_affirmative(self.instance.get('disable_spark_job_stage_tags', False))
        self._disable_spark_stage_metrics = is_affirmative(self.instance.get('disable_spark_stage_metrics', False))

        # Get the cluster name from the instance configuration
        self.cluster_name = self.instance.get('cluster_name')
        if self.cluster_name is None:
            raise ConfigurationError('The cluster_name must be specified in the instance configuration')

        self.master_address = self._get_master_address()
        self._connection_error_seen = False
        self._debounced_this_run = False

    def check(self, _):
        self._debounced_this_run = False

        tags = list(self.tags)

        tags.append('spark_cluster:%s' % self.cluster_name)
        if not self._disable_legacy_cluster_tag:
            tags.append('cluster_name:%s' % self.cluster_name)

        spark_apps = self._get_running_apps()

        if not spark_apps:
            self.log.warning('No running apps found. No metrics will be collected.')
            return

        # Get the job metrics
        self._spark_job_metrics(spark_apps, tags)

        if not self._disable_spark_stage_metrics:
            # Get the stage metrics
            self._spark_stage_metrics(spark_apps, tags)

        # Get the executor metrics
        self._spark_executor_metrics(spark_apps, tags)

        # Get the rdd metrics
        self._spark_rdd_metrics(spark_apps, tags)

        # Get the streaming statistics metrics
        if is_affirmative(self.instance.get('streaming_metrics', True)):
            self._spark_streaming_statistics_metrics(spark_apps, tags)
            self._spark_structured_streams_metrics(spark_apps, tags)

        # Report success after gathering all metrics from the ApplicationMaster
        if spark_apps:
            _, (_, tracking_url) = next(iter(spark_apps.items()))
            base_url = self._get_request_url(tracking_url)
            am_address = self._get_url_base(base_url)

            self.service_check(
                SPARK_SERVICE_CHECK,
                AgentCheck.OK,
                tags=['url:%s' % am_address] + tags,
            )

    def _get_master_address(self):
        """
        Get the master address from the instance configuration
        """

        master_address = self.instance.get(MASTER_ADDRESS)
        if master_address is None:
            master_address = self.instance.get(DEPRECATED_MASTER_ADDRESS)

            if master_address:
                self.log.warning(
                    'The use of `%s` is deprecated. Please use `%s` instead.', DEPRECATED_MASTER_ADDRESS, MASTER_ADDRESS
                )
            else:
                raise ConfigurationError(
                    'URL for `%s` must be specified in the instance configuration' % MASTER_ADDRESS
                )

        return master_address

    def _get_request_url(self, url):
        """
        Get the request address, build with proxy if necessary
        """
        parsed = urlparse(url)

        _url = url
        if not (parsed.netloc and parsed.scheme) and is_affirmative(self.instance.get('spark_proxy_enabled', False)):
            _url = urljoin(self.master_address, parsed.path)

        self.log.debug('Request URL returned: %s', _url)
        return _url

    def _get_running_apps(self):
        """
        Determine what mode was specified
        """
        tags = list(self.tags)

        tags.append('spark_cluster:%s' % self.cluster_name)
        if not self._disable_legacy_cluster_tag:
            tags.append('cluster_name:%s' % self.cluster_name)

        if self.cluster_mode == SPARK_STANDALONE_MODE:
            # check for PRE-20
            pre20 = is_affirmative(self.instance.get(SPARK_PRE_20_MODE, False))
            return self._standalone_init(pre20, tags)

        elif self.cluster_mode == SPARK_MESOS_MODE:
            running_apps = self._mesos_init(tags)
            return self._get_spark_app_ids(running_apps, tags)

        elif self.cluster_mode == SPARK_YARN_MODE:
            running_apps = self._yarn_init(tags)
            return self._get_spark_app_ids(running_apps, tags)

        elif self.cluster_mode == SPARK_DRIVER_MODE:
            return self._driver_init(tags)

        else:
            raise Exception('Invalid setting for %s. Received %s.' % (SPARK_CLUSTER_MODE, self.cluster_mode))

    def _collect_version(self, base_url, tags):
        try:
            version_json = self._rest_request_to_json(base_url, SPARK_VERSION_PATH, SPARK_SERVICE_CHECK, tags)
            if version_json is None:
                return False
            version = version_json['spark']
        except Exception as e:
            self.log.debug("Failed to collect version information: %s", e)
            return False
        else:
            self.set_metadata('version', version)
            return True

    def _driver_init(self, tags):
        """
        Return a dictionary of {app_id: (app_name, tracking_url)} for the running Spark applications
        """
        self._collect_version(self.master_address, tags)
        running_apps = {}

        # A request earlier in this check run already hit a debounced connection failure.
        # Skip the remaining driver queries so we only retry on the next scheduled run.
        if self._debounced_this_run:
            return running_apps
        metrics_json = self._rest_request_to_json(
            self.master_address, SPARK_APPS_PATH, SPARK_DRIVER_SERVICE_CHECK, tags
        )

        if metrics_json is None:
            return running_apps

        for app_json in metrics_json:
            app_id = app_json.get('id')
            app_name = app_json.get('name')
            running_apps[app_id] = (app_name, self.master_address)

        self.service_check(
            SPARK_DRIVER_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % self.master_address] + tags,
        )
        self.log.info("Returning running apps %s", running_apps)
        return running_apps

    def _standalone_init(self, pre_20_mode, tags):
        """
        Return a dictionary of {app_id: (app_name, tracking_url)} for the running Spark applications
        """
        metrics_json = self._rest_request_to_json(
            self.master_address, SPARK_MASTER_STATE_PATH, SPARK_STANDALONE_SERVICE_CHECK, tags
        )

        if metrics_json is None:
            return {}

        running_apps = {}
        version_set = False

        if metrics_json.get('activeapps'):
            for app in metrics_json['activeapps']:
                app_id = app.get('id')
                app_name = app.get('name')

                # Parse through the HTML to grab the application driver's link
                try:
                    app_url = self._get_standalone_app_url(app_id, tags)

                    if app_id and app_name and app_url:
                        if not version_set:
                            version_set = self._collect_version(app_url, tags)
                        if pre_20_mode:
                            self.log.debug('Getting application list in pre-20 mode')
                            applist = self._rest_request_to_json(
                                app_url, SPARK_APPS_PATH, SPARK_STANDALONE_SERVICE_CHECK, tags
                            )
                            if applist:
                                for appl in applist:
                                    aid = appl.get('id')
                                    aname = appl.get('name')
                                    running_apps[aid] = (aname, app_url)
                        else:
                            running_apps[app_id] = (app_name, app_url)
                except Exception:
                    # it's possible for the requests to fail if the job
                    # completed since we got the list of apps.  Just continue
                    pass

        # Report success after gathering metrics from Spark master
        self.service_check(
            SPARK_STANDALONE_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % self.master_address] + tags,
        )
        self.log.info("Returning running apps %s", running_apps)
        return running_apps

    def _mesos_init(self, tags):
        """
        Return a dictionary of {app_id: (app_name, tracking_url)} for running Spark applications.
        """
        running_apps = {}

        metrics_json = self._rest_request_to_json(self.master_address, MESOS_MASTER_APP_PATH, MESOS_SERVICE_CHECK, tags)

        if metrics_json is None:
            return running_apps

        if metrics_json.get('frameworks'):
            for app_json in metrics_json.get('frameworks'):
                app_id = app_json.get('id')
                tracking_url = app_json.get('webui_url')
                app_name = app_json.get('name')

                if app_id and tracking_url and app_name:
                    spark_ports = self.instance.get('spark_ui_ports')
                    if spark_ports is None:
                        # No filtering by port, just return all the frameworks
                        running_apps[app_id] = (app_name, tracking_url)
                    else:
                        # Only return the frameworks running on the correct port
                        tracking_url_port = urlparse(tracking_url).port
                        if tracking_url_port in spark_ports:
                            running_apps[app_id] = (app_name, tracking_url)

        # Report success after gathering all metrics from ResourceManager
        self.service_check(
            MESOS_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % self.master_address] + tags,
        )

        return running_apps

    def _yarn_init(self, tags):
        """
        Return a dictionary of {app_id: (app_name, tracking_url)} for running Spark applications.
        """
        running_apps = self._yarn_get_running_spark_apps(tags)

        # Report success after gathering all metrics from ResourceManager
        self.service_check(
            YARN_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % self.master_address] + tags,
        )

        return running_apps

    def _get_standalone_app_url(self, app_id, tags):
        """
        Return the application URL from the app info page on the Spark master.
        Due to a bug, we need to parse the HTML manually because we cannot
        fetch JSON data from HTTP interface.
        """
        app_page = self._rest_request(
            self.master_address, SPARK_MASTER_APP_PATH, SPARK_STANDALONE_SERVICE_CHECK, tags, appId=app_id
        )

        if app_page is None:
            return None

        dom = BeautifulSoup(app_page.text, 'html.parser')
        app_detail_ui_links = dom.find_all('a', string='Application Detail UI')

        if app_detail_ui_links and len(app_detail_ui_links) == 1:
            return app_detail_ui_links[0].attrs['href']

    def _yarn_get_running_spark_apps(self, tags):
        """
        Return a dictionary of {app_id: (app_name, tracking_url)} for running Spark applications.

        The `app_id` returned is that of the YARN application. This will eventually be mapped into
        a Spark application ID.
        """
        metrics_json = self._rest_request_to_json(
            self.master_address,
            YARN_APPS_PATH,
            YARN_SERVICE_CHECK,
            tags,
            states=APPLICATION_STATES,
            applicationTypes=YARN_APPLICATION_TYPES,
        )

        if metrics_json is None:
            return {}

        running_apps = {}

        if metrics_json.get('apps'):
            if metrics_json['apps'].get('app') is not None:
                for app_json in metrics_json['apps']['app']:
                    app_id = app_json.get('id')
                    tracking_url = app_json.get('trackingUrl')
                    app_name = app_json.get('name')

                    if app_id and tracking_url and app_name:
                        running_apps[app_id] = (app_name, tracking_url)

        return running_apps

    def _get_spark_app_ids(self, running_apps, tags):
        """
        Traverses the Spark application master in YARN to get a Spark application ID.

        Return a dictionary of {app_id: (app_name, tracking_url)} for Spark applications
        """
        spark_apps = {}
        version_set = False
        for app_id, (app_name, tracking_url) in running_apps.items():
            try:
                if not version_set:
                    version_set = self._collect_version(tracking_url, tags)
                response = self._rest_request_to_json(tracking_url, SPARK_APPS_PATH, SPARK_SERVICE_CHECK, tags)
                if response is None:
                    continue
            except Exception as e:
                self.log.warning("Exception happened when fetching app ids for %s: %s", tracking_url, e)
                continue

            for app in response:
                app_id = app.get('id')
                app_name = app.get('name')

                if app_id and app_name:
                    spark_apps[app_id] = (app_name, tracking_url)

        return spark_apps

    def _describe_app(self, property, running_apps, addl_tags):
        """
        Get payloads that describe certain property of the running apps.
        Examples of properties:
        - the app's jobs
        - the app's spark stages
        """
        for app_id, (app_name, tracking_url) in running_apps.items():
            base_url = self._get_request_url(tracking_url)
            try:
                response = self._rest_request(
                    base_url, SPARK_APPS_PATH, SPARK_SERVICE_CHECK, addl_tags, app_id, property
                )
                if response is None:
                    continue
            except HTTPError:
                self.log.debug("Got an error collecting %s", property, exc_info=True)
                continue
            try:
                yield (response.json(), [f'app_name:{app_name}'] + addl_tags)
            except JSONDecodeError:
                self.log.debug(
                    'Skipping metrics for %s from app %s due to unparsable JSON payload.', property, app_name
                )
                continue

    def _spark_job_metrics(self, running_apps, addl_tags):
        """
        Get metrics for each Spark job.
        """
        for jobs, app_tags in self._describe_app('jobs', running_apps, addl_tags):
            for job in jobs:
                job_tags = []

                status = job.get('status')
                job_tags.append('status:%s' % str(status).lower())

                job_id = job.get('jobId')
                if job_id is not None:
                    job_tags.append('job_id:{}'.format(job_id))

                if not self._disable_spark_job_stage_tags:
                    for stage_id in job.get('stageIds', []):
                        job_tags.append('stage_id:{}'.format(stage_id))

                tags = app_tags + job_tags
                self._set_metrics_from_json(tags, job, SPARK_JOB_METRICS)
                self._set_metric('spark.job.count', COUNT, 1, tags)

    def _spark_stage_metrics(self, running_apps, addl_tags):
        """
        Get metrics for each Spark stage.
        """
        for stages, app_tags in self._describe_app('stages', running_apps, addl_tags):
            for stage in stages:
                stage_tags = []

                status = stage.get('status')
                stage_tags.append('status:%s' % str(status).lower())

                stage_id = stage.get('stageId')
                if stage_id is not None:
                    stage_tags.append('stage_id:{}'.format(stage_id))

                tags = app_tags + stage_tags
                self._set_metrics_from_json(tags, stage, SPARK_STAGE_METRICS)
                self._set_metric('spark.stage.count', COUNT, 1, tags)

    def _spark_executor_metrics(self, running_apps, addl_tags):
        """
        Get metrics for each Spark executor.
        """
        for executors, app_tags in self._describe_app('executors', running_apps, addl_tags):
            for executor in executors:
                if executor.get('id') == 'driver':
                    self._set_metrics_from_json(app_tags, executor, SPARK_DRIVER_METRICS)
                else:
                    self._set_metrics_from_json(app_tags, executor, SPARK_EXECUTOR_METRICS)

                    if is_affirmative(self.instance.get('executor_level_metrics', False)):
                        self._set_metrics_from_json(
                            app_tags + ['executor_id:{}'.format(executor.get('id', 'unknown'))],
                            executor,
                            SPARK_EXECUTOR_LEVEL_METRICS,
                        )

            if executors:
                self._set_metric('spark.executor.count', COUNT, len(executors), app_tags)

    def _spark_rdd_metrics(self, running_apps, addl_tags):
        """
        Get metrics for each Spark RDD.
        """
        for rdds, app_tags in self._describe_app('storage/rdd', running_apps, addl_tags):
            for rdd in rdds:
                self._set_metrics_from_json(app_tags, rdd, SPARK_RDD_METRICS)

            if rdds:
                self._set_metric('spark.rdd.count', COUNT, len(rdds), app_tags)

    def _spark_streaming_statistics_metrics(self, running_apps, addl_tags):
        """
        Get metrics for each application streaming statistics.
        """
        for stats, app_tags in self._describe_app('streaming/statistics', running_apps, addl_tags):
            self.log.debug('streaming/statistics: %s', stats)
            self._set_metrics_from_json(app_tags, stats, SPARK_STREAMING_STATISTICS_METRICS)

    def _spark_structured_streams_metrics(self, running_apps, addl_tags):
        """
        Get metrics for each application structured stream.
        Requires:
        - The Metric Servlet to be enabled to path <APP_URL>/metrics/json (enabled by default)
        - `SET spark.sql.streaming.metricsEnabled=true` in the app
        """

        for app_name, tracking_url in running_apps.values():
            try:
                base_url = self._get_request_url(tracking_url)
                response = self._rest_request_to_json(
                    base_url, self.metricsservlet_path, SPARK_SERVICE_CHECK, addl_tags
                )
                if response is None:
                    continue
                self.log.debug('Structured streaming metrics: %s', response)
                response = {
                    metric_name: v['value']
                    for metric_name, v in response.get('gauges').items()
                    if 'streaming' in metric_name and 'value' in v
                }
                for gauge_name, value in response.items():
                    match = STRUCTURED_STREAMS_METRICS_REGEX.match(gauge_name)
                    if not match:
                        self.log.debug("No regex match found for gauge: '%s'", str(gauge_name))
                        continue
                    groups = match.groupdict()
                    metric_name = groups['metric_name']
                    if metric_name not in SPARK_STRUCTURED_STREAMING_METRICS:
                        self.log.debug("Unknown metric_name encountered: '%s'", str(metric_name))
                        continue
                    metric_name, submission_type = SPARK_STRUCTURED_STREAMING_METRICS[metric_name]
                    tags = ['app_name:%s' % str(app_name)]
                    tags.extend(addl_tags)

                    if self._enable_query_name_tag:
                        query_name = groups['query_name']
                        match = UUID_REGEX.match(query_name)
                        if not match:
                            tags.append('query_name:%s' % str(query_name))
                        else:
                            self.log.debug(
                                'Cannot attach `query_name` tag. Add a query name to collect this tag for %s',
                                query_name,
                            )

                    self._set_metric(metric_name, submission_type, value, tags=tags)
            except HTTPError as e:
                self.log.debug("No structured streaming metrics to collect from app %s. %s", app_name, e, exc_info=True)
                pass

    def _set_metrics_from_json(self, tags, metrics_json, metrics):
        """
        Parse the JSON response and set the metrics
        """
        if metrics_json is None:
            return

        for status, (metric_name, metric_type) in metrics.items():
            # Metrics defined with a dot `.` are exposed in a nested dictionary.
            # {"foo": {"bar": "baz", "qux": "quux"}}
            #   foo.bar -> baz
            #   foo.qux -> quux
            if '.' in status:
                parent_key, child_key = status.split('.')
                metric_status = metrics_json.get(parent_key, {}).get(child_key)
            else:
                metric_status = metrics_json.get(status)

            if metric_status is not None:
                self._set_metric(metric_name, metric_type, metric_status, tags)

    def _set_metric(self, metric_name, metric_type, value, tags=None):
        """
        Set a metric
        """
        if tags is None:
            tags = []
        if metric_type == GAUGE:
            self.gauge(metric_name, value, tags=tags)
        elif metric_type == COUNT:
            self.count(metric_name, value, tags=tags)
        elif metric_type == MONOTONIC_COUNT:
            self.monotonic_count(metric_name, value, tags=tags)
        else:
            self.log.error('Metric type "%s" unknown', metric_type)

    def _rest_request(self, url, object_path, service_name, tags, *args, **kwargs):
        """
        Query the given URL and return the response
        """
        service_check_tags = ['url:%s' % self._get_url_base(url)] + tags

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add args to the url
        if args:
            for directory in args:
                url = self._join_url_dir(url, directory)

        # Add proxyapproved=True if we already have the proxy cookie
        if self.proxy_redirect_cookies:
            kwargs["proxyapproved"] = 'true'

        # Add kwargs as arguments
        if kwargs:
            query = '&'.join(['{0}={1}'.format(key, value) for key, value in kwargs.items()])
            url = urljoin(url, '?' + query)

        try:
            self.log.debug('Spark check URL: %s', url)
            response = self.http.get(url, cookies=self.proxy_redirect_cookies)
            response.raise_for_status()

            # Reset connection errors on success
            self._connection_error_seen = False

            content = response.text
            proxy_redirect_url = self._parse_proxy_redirect_url(content)
            if proxy_redirect_url:
                self.proxy_redirect_cookies = response.cookies
                # When using a proxy and the remote user is different that the current user
                # spark will display an html warning page.
                # This page displays a redirect link (which appends `proxyapproved=true`) and also
                # sets a cookie to the current http session. Let's follow the link.
                # https://github.com/apache/hadoop/blob/2064ca015d1584263aac0cc20c60b925a3aff612/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-web-proxy/src/main/java/org/apache/hadoop/yarn/server/webproxy/WebAppProxyServlet.java#L368
                response = self.http.get(proxy_redirect_url, cookies=self.proxy_redirect_cookies)
                response.raise_for_status()

        except Timeout as e:
            self.service_check(
                service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message='Request timeout: {0}, {1}'.format(url, e),
            )
            raise

        except (HTTPError, InvalidURL, ConnectionError) as e:
            if isinstance(e, ConnectionError) and self._should_suppress_connection_error(e, tags):
                return None

            self.service_check(
                service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message='Request failed: {0}, {1}'.format(url, e),
            )
            raise

        except ValueError as e:
            self.service_check(service_name, AgentCheck.CRITICAL, tags=service_check_tags, message=str(e))
            raise

        else:
            return response

    def _rest_request_to_json(self, address, object_path, service_name, tags, *args, **kwargs):
        """
        Query the given URL and return the JSON response
        """
        response = self._rest_request(address, object_path, service_name, tags, *args, **kwargs)

        if response is None:
            return None

        try:
            response_json = response.json()

        except JSONDecodeError as e:
            response_text = response.text.strip()
            if response_text and 'spark is starting up' in response_text.lower():
                self.log.debug("Spark driver not ready yet at %s: %s", self._get_url_base(address), response_text)
                return None
            self.service_check(
                service_name,
                AgentCheck.CRITICAL,
                tags=['url:%s' % self._get_url_base(address)] + tags,
                message='JSON Parse failed: {0}'.format(e),
            )
            raise

        return response_json

    def _should_suppress_connection_error(self, exception, tags):
        """Suppress kubernetes-only connection false positives during pod shutdown."""
        pod_phase = self._get_pod_phase(tags)
        if pod_phase is None:
            return False

        if pod_phase in ('failed', 'succeeded', 'unknown'):
            self.log.debug("Pod phase is terminal, suppressing request error: %s", exception)
            return True

        if (
            not self._connection_error_seen
            and not self._debounced_this_run
            and ("Connection refused" in str(exception) or "No route to host" in str(exception))
        ):
            self._connection_error_seen = True
            self._debounced_this_run = True
            self.log.warning(
                "Connection failed. Suppressing error once to ensure driver is running. Error: %s",
                exception,
            )
            return True

        return False

    @staticmethod
    def _get_pod_phase(tags):
        for tag in tags or []:
            if tag.startswith('pod_phase:'):
                return tag.split(':', 1)[1].strip().lower()
        return None

    @classmethod
    def _join_url_dir(cls, url, *args):
        """
        Join a URL with multiple directories
        """
        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url

    @classmethod
    def _get_url_base(cls, url):
        """
        Return the base of a URL
        """
        s = urlsplit(url)
        return urlunsplit([s.scheme, s.netloc, '', '', ''])

    @staticmethod
    def _parse_proxy_redirect_url(html_content):
        """When the spark proxy returns a warning page with a redirect link, this link has to be parsed
        from the html content."""
        if not html_content[:6] == "<html>":  # Prevent html parsing of non-html content.
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        redirect_link = None
        for link in soup.find_all('a'):
            href = link.get('href')
            if 'proxyapproved' in href:
                redirect_link = href
                break

        return redirect_link
