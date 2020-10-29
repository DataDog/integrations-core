# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
from simplejson import JSONDecodeError
from six import iteritems, itervalues
from six.moves.urllib.parse import urljoin, urlsplit, urlunsplit

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.mapreduce.metrics import (
    HISTOGRAM,
    INCREMENT,
    MAPREDUCE_JOB_COUNTER_METRICS,
    MAPREDUCE_JOB_METRICS,
    MAPREDUCE_MAP_TASK_METRICS,
    MAPREDUCE_REDUCE_TASK_METRICS,
)


class MapReduceCheck(AgentCheck):

    HTTP_CONFIG_REMAPPER = {'ssl_verify': {'name': 'tls_verify'}}

    # Default Settings
    DEFAULT_CLUSTER_NAME = 'default_cluster'

    # Service Check Names
    YARN_SERVICE_CHECK = 'mapreduce.resource_manager.can_connect'
    MAPREDUCE_SERVICE_CHECK = 'mapreduce.application_master.can_connect'

    # URL Paths
    CLUSTER_INFO = 'ws/v1/cluster'
    YARN_APPS_PATH = 'ws/v1/cluster/apps'
    MAPREDUCE_JOBS_PATH = 'ws/v1/mapreduce/jobs'

    # Application type and states to collect
    YARN_APPLICATION_TYPES = 'MAPREDUCE'
    YARN_APPLICATION_STATES = 'RUNNING'

    def __init__(self, name, init_config, instances):
        super(MapReduceCheck, self).__init__(name, init_config, instances)

        # Parse job specific counters
        self.general_counters = self._parse_general_counters(init_config)

        # Parse job specific counters
        self.job_specific_counters = self._parse_job_specific_counters(init_config)

        # Get properties from conf file
        self.rm_address = self.instance.get('resourcemanager_uri')
        if self.rm_address is None:
            raise ConfigurationError("The ResourceManager URL must be specified in the instance configuration")
        self.collect_task_metrics = is_affirmative(self.instance.get('collect_task_metrics', False))

        # Get additional tags from the conf file
        self.custom_tags = list(set(self.instance.get("tags", [])))

        # Get the cluster name from the conf file
        cluster_name = self.instance.get('cluster_name')
        if cluster_name is None:
            self.warning(
                "The cluster_name must be specified in the instance configuration, defaulting to '%s'",
                self.DEFAULT_CLUSTER_NAME,
            )
            cluster_name = self.DEFAULT_CLUSTER_NAME
        self.metric_tags = self.custom_tags + ['cluster_name:{}'.format(cluster_name)]

    def check(self, _):
        # Get the running MR applications from YARN
        running_apps = self._get_running_app_ids()

        # Report success after gathering all metrics from ResourceManaager
        self.service_check(
            self.YARN_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:{}'.format(self.rm_address)] + self.custom_tags,
            message='Connection to ResourceManager "{}" was successful'.format(self.rm_address),
        )

        # Get the applications from the application master
        running_jobs = self._mapreduce_job_metrics(running_apps, self.metric_tags)

        # # Get job counter metrics
        self._mapreduce_job_counters_metrics(running_jobs, self.metric_tags)

        # Get task metrics
        if self.collect_task_metrics:
            self._mapreduce_task_metrics(running_jobs, self.metric_tags)

        # Report success after gathering all metrics from Application Master
        if running_jobs:
            job_id, metrics = next(iteritems(running_jobs))
            am_address = self._get_url_base(metrics['tracking_url'])

            self.service_check(
                self.MAPREDUCE_SERVICE_CHECK,
                AgentCheck.OK,
                tags=['url:{}'.format(am_address)] + self.custom_tags,
                message='Connection to ApplicationManager "{}" was successful'.format(am_address),
            )
        self._get_hadoop_version()

    def _parse_general_counters(self, init_config):
        """
        Return a dictionary for each job counter
        {
          counter_group_name: [
              counter_name
            ]
          }
        }
        """
        job_counter = {}

        if init_config.get('general_counters'):

            # Parse the custom metrics
            for counter_group in init_config['general_counters']:
                counter_group_name = counter_group.get('counter_group_name')
                counters = counter_group.get('counters')

                if not counter_group_name:
                    raise Exception('"general_counters" must contain a valid "counter_group_name"')

                if not counters:
                    raise Exception('"general_counters" must contain a list of "counters"')

                # Add the counter_group to the job_counters if it doesn't already exist
                if counter_group_name not in job_counter:
                    job_counter[counter_group_name] = []

                for counter in counters:
                    counter_name = counter.get('counter_name')

                    if not counter_name:
                        raise Exception('At least one "counter_name" should be specified in the list of "counters"')

                    job_counter[counter_group_name].append(counter_name)

        return job_counter

    def _parse_job_specific_counters(self, init_config):
        """
        Return a dictionary for each job counter
        {
          job_name: {
            counter_group_name: [
                counter_name
              ]
            }
          }
        }
        """
        job_counter = {}

        if init_config.get('job_specific_counters'):

            # Parse the custom metrics
            for job in init_config['job_specific_counters']:
                job_name = job.get('job_name')
                metrics = job.get('metrics')

                if not job_name:
                    raise Exception('Counter metrics must have a "job_name"')

                if not metrics:
                    raise Exception("Jobs specified in counter metrics must contain at least one metric")

                # Add the job to the custom metrics if it doesn't already exist
                if job_name not in job_counter:
                    job_counter[job_name] = {}

                for metric in metrics:
                    counter_group_name = metric.get('counter_group_name')
                    counters = metric.get('counters')

                    if not counter_group_name:
                        raise Exception('Each counter metric must contain a valid "counter_group_name"')

                    if not counters:
                        raise Exception('Each counter metric must contain a list of "counters"')

                    # Add the counter group name if it doesn't exist for the current job
                    if counter_group_name not in job_counter[job_name]:
                        job_counter[job_name][counter_group_name] = []

                    for counter in counters:
                        counter_name = counter.get('counter_name')

                        if not counter_name:
                            raise Exception('At least one "counter_name" should be specified in the list of "counters"')

                        job_counter[job_name][counter_group_name].append(counter_name)

        return job_counter

    def _get_hadoop_version(self):
        if not self.is_metadata_collection_enabled():
            return
        try:
            cluster_info = self._rest_request_to_json(self.rm_address, self.CLUSTER_INFO)
            hadoop_version = cluster_info.get('clusterInfo', {}).get('hadoopVersion', '')
            if hadoop_version:
                self.set_metadata('version', hadoop_version)
        except Exception as e:
            self.log.warning("There was an error retrieving hadoop version {}", e)

    def _get_running_app_ids(self):
        """
        Return a dictionary of {app_id: (app_name, tracking_url)} for the running MapReduce applications
        """
        metrics_json = self._rest_request_to_json(
            self.rm_address,
            self.YARN_APPS_PATH,
            self.YARN_SERVICE_CHECK,
            states=self.YARN_APPLICATION_STATES,
            applicationTypes=self.YARN_APPLICATION_TYPES,
        )

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

    def _mapreduce_job_metrics(self, running_apps, addl_tags):
        """
        Get metrics for each MapReduce job.
        Return a dictionary for each MapReduce job
        {
          job_id: {
            'job_name': job_name,
            'app_name': app_name,
            'user_name': user_name,
            'tracking_url': tracking_url
        }
        """
        running_jobs = {}

        for app_name, tracking_url in itervalues(running_apps):

            metrics_json = self._rest_request_to_json(
                tracking_url, self.MAPREDUCE_JOBS_PATH, self.MAPREDUCE_SERVICE_CHECK
            )

            if metrics_json.get('jobs'):
                if metrics_json['jobs'].get('job'):

                    for job_json in metrics_json['jobs']['job']:
                        job_id = job_json.get('id')
                        job_name = job_json.get('name')
                        user_name = job_json.get('user')

                        if job_id and job_name and user_name:

                            # Build the structure to hold the information for each job ID
                            running_jobs[str(job_id)] = {
                                'job_name': str(job_name),
                                'app_name': str(app_name),
                                'user_name': str(user_name),
                                'tracking_url': self._join_url_dir(tracking_url, self.MAPREDUCE_JOBS_PATH, job_id),
                            }

                            tags = [
                                'app_name:' + str(app_name),
                                'user_name:' + str(user_name),
                                'job_name:' + str(job_name),
                            ]

                            tags.extend(addl_tags)

                            self._set_metrics_from_json(job_json, MAPREDUCE_JOB_METRICS, tags)

        return running_jobs

    def _mapreduce_job_counters_metrics(self, running_jobs, addl_tags):
        """
        Get custom metrics specified for each counter
        """
        for job_metrics in itervalues(running_jobs):
            job_name = job_metrics['job_name']

            # Check if the job_name exist in the custom metrics
            if self.general_counters or (job_name in self.job_specific_counters):
                job_specific_metrics = self.job_specific_counters.get(job_name)

                metrics_json = self._rest_request_to_json(
                    job_metrics['tracking_url'], 'counters', self.MAPREDUCE_SERVICE_CHECK, tags=addl_tags
                )

                if metrics_json.get('jobCounters'):
                    if metrics_json['jobCounters'].get('counterGroup'):

                        # Cycle through all the counter groups for this job
                        for counter_group in metrics_json['jobCounters']['counterGroup']:
                            group_name = counter_group.get('counterGroupName')

                            if group_name:
                                counter_metrics = set([])

                                # Add any counters in the job specific metrics
                                if job_specific_metrics and group_name in job_specific_metrics:
                                    counter_metrics = counter_metrics.union(job_specific_metrics[group_name])

                                # Add any counters in the general metrics
                                if group_name in self.general_counters:
                                    counter_metrics = counter_metrics.union(self.general_counters[group_name])

                                if counter_metrics:
                                    # Cycle through all the counters in this counter group
                                    if counter_group.get('counter'):
                                        for counter in counter_group['counter']:
                                            counter_name = counter.get('name')

                                            # Check if the counter name is in the custom metrics for this group name
                                            if counter_name and counter_name in counter_metrics:
                                                tags = [
                                                    'app_name:' + job_metrics.get('app_name'),
                                                    'user_name:' + job_metrics.get('user_name'),
                                                    'job_name:' + job_name,
                                                    'counter_name:' + str(counter_name).lower(),
                                                ]

                                                tags.extend(addl_tags)

                                                self._set_metrics_from_json(
                                                    counter, MAPREDUCE_JOB_COUNTER_METRICS, tags
                                                )

    def _mapreduce_task_metrics(self, running_jobs, addl_tags):
        """
        Get metrics for each MapReduce task
        Return a dictionary of {task_id: 'tracking_url'} for each MapReduce task
        """
        for job_stats in itervalues(running_jobs):

            metrics_json = self._rest_request_to_json(
                job_stats['tracking_url'], 'tasks', self.MAPREDUCE_SERVICE_CHECK, tags=addl_tags
            )

            if metrics_json.get('tasks'):
                if metrics_json['tasks'].get('task'):

                    for task in metrics_json['tasks']['task']:
                        task_type = task.get('type')

                        if task_type:
                            tags = [
                                'app_name:' + job_stats['app_name'],
                                'user_name:' + job_stats['user_name'],
                                'job_name:' + job_stats['job_name'],
                                'task_type:' + str(task_type).lower(),
                            ]

                            tags.extend(addl_tags)

                            if task_type == 'MAP':
                                self._set_metrics_from_json(task, MAPREDUCE_MAP_TASK_METRICS, tags)

                            elif task_type == 'REDUCE':
                                self._set_metrics_from_json(task, MAPREDUCE_REDUCE_TASK_METRICS, tags)

    def _set_metrics_from_json(self, metrics_json, metrics, tags):
        """
        Parse the JSON response and set the metrics
        """
        for status, (metric_name, metric_type) in iteritems(metrics):
            metric_status = metrics_json.get(status)

            if metric_status is not None:
                self._set_metric(metric_name, metric_type, metric_status, tags=tags)

    def _set_metric(self, metric_name, metric_type, value, tags=None, device_name=None):
        """
        Set a metric
        """
        if metric_type == HISTOGRAM:
            self.histogram(metric_name, value, tags=tags, device_name=device_name)
        elif metric_type == INCREMENT:
            self.increment(metric_name, value, tags=tags, device_name=device_name)
        else:
            self.log.error('Metric type "%s" unknown', metric_type)

    def _rest_request_to_json(self, address, object_path, service_name=None, tags=None, *args, **kwargs):
        """
        Query the given URL and return the JSON response
        """
        tags = [] if tags is None else tags

        service_check_tags = ['url:{}'.format(self._get_url_base(address))] + tags

        url = address

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add args to the url
        if args:
            for directory in args:
                url = self._join_url_dir(url, directory)

        self.log.debug('Attempting to connect to "%s"', url)

        # Add kwargs as arguments
        if kwargs:
            query = '&'.join(['{}={}'.format(key, value) for key, value in iteritems(kwargs)])
            url = urljoin(url, '?' + query)

        try:
            response = self.http.get(url)
            response.raise_for_status()
            response_json = response.json()

        except Timeout as e:
            self._critical_service(service_name, service_check_tags, "Request timeout: {}, {}".format(url, e))
            raise

        except (HTTPError, InvalidURL, ConnectionError) as e:
            self._critical_service(service_name, service_check_tags, "Request failed: {}, {}".format(url, e))
            raise

        except JSONDecodeError as e:
            self._critical_service(service_name, service_check_tags, "JSON Parse failed: {}, {}".format(url, e))
            raise

        except ValueError as e:
            self._critical_service(service_name, service_check_tags, str(e))
            raise

        return response_json

    def _critical_service(self, service_name, tags, message):
        if service_name:
            self.service_check(service_name, AgentCheck.CRITICAL, tags=tags, message=message)

    def _join_url_dir(self, url, *args):
        """
        Join a URL with multiple directories
        """
        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url

    def _get_url_base(self, url):
        """
        Return the base of a URL
        """
        s = urlsplit(url)
        return urlunsplit([s.scheme, s.netloc, '', '', ''])
