# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from fnmatch import fnmatchcase
from ...errors import CheckException
import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from math import isnan, isinf
from prometheus_client.parser import text_fd_to_metric_families

from six import PY3, iteritems, string_types

from .. import AgentCheck

from datadog_checks.config import is_affirmative

if PY3:
    long = int

class OpenMetricsScraperMixin(object):
    # pylint: disable=E1101
    # This class is not supposed to be used by itself, it provides scraping behavior but
    # need to be within a check in the end

    REQUESTS_CHUNK_SIZE = 1024 * 10  # use 10kb as chunk size when using the Stream feature in requests.get
    # indexes in the sample tuple of core.Metric
    SAMPLE_NAME = 0
    SAMPLE_LABELS = 1
    SAMPLE_VALUE = 2

    METRIC_TYPES = ['counter', 'gauge', 'summary', 'histogram']

    def __init__(self, *args, **kwargs):
        # Initialize AgentCheck's base class
        super(OpenMetricsScraperMixin, self).__init__(*args, **kwargs)

    def create_scraper_configuration(self, instance=None):

        # We can choose to create a default mixin configuration for an empty instance
        if instance is None:
            instance = {}

        # Create an empty configuration
        config = {}

        # Set the endpoint
        endpoint = instance.get('prometheus_url')
        if instance and endpoint is None:
            raise CheckException("You have to define a prometheus_url for each prometheus instance")

        config['prometheus_url'] = endpoint

        # `NAMESPACE` is the prefix metrics will have. Need to be hardcoded in the
        # child check class.
        namespace = instance.get('namespace')
        # Check if we have a namespace
        if instance and namespace is None:
            if self.default_namespace is None:
                raise CheckException("You have to define a namespace for each prometheus check")
            namespace = self.default_namespace

        config['namespace'] = namespace

        # Retrieve potential default instance settings for the namespace
        default_instance = self.default_instances.get(namespace, {})

        # `metrics_mapper` is a dictionary where the keys are the metrics to capture
        # and the values are the corresponding metrics names to have in datadog.
        # Note: it is empty in the parent class but will need to be
        # overloaded/hardcoded in the final check not to be counted as custom metric.

        # Metrics are preprocessed if no mapping
        metrics_mapper = {}
        # We merge list and dictionaries from optional defaults & instance settings
        metrics = default_instance.get('metrics', []) + instance.get('metrics', [])
        for metric in metrics:
            if isinstance(metric, string_types):
                metrics_mapper[metric] = metric
            else:
                metrics_mapper.update(metric)

        config['metrics_mapper'] = metrics_mapper

        # `_metrics_wildcards` holds the potential wildcards to match for metrics
        config['_metrics_wildcards'] = None

        # `prometheus_metrics_prefix` allows to specify a prefix that all
        # prometheus metrics should have. This can be used when the prometheus
        # endpoint we are scrapping allows to add a custom prefix to it's
        # metrics.
        config['prometheus_metrics_prefix'] = instance.get('prometheus_metrics_prefix',
                                                           default_instance.get('prometheus_metrics_prefix', ''))

        # `label_joins` holds the configuration for extracting 1:1 labels from
        # a target metric to all metric matching the label, example:
        # self.label_joins = {
        #     'kube_pod_info': {
        #         'label_to_match': 'pod',
        #         'labels_to_get': ['node', 'host_ip']
        #     }
        # }
        config['label_joins'] = default_instance.get('label_joins', {})
        config['label_joins'].update(instance.get('label_joins', {}))

        # `_label_mapping` holds the additionals label info to add for a specific
        # label value, example:
        # self._label_mapping = {
        #     'pod': {
        #         'dd-agent-9s1l1': [("node","yolo"),("host_ip","yey")]
        #     }
        # }
        config['_label_mapping'] = {}

        # `_active_label_mapping` holds a dictionary of label values found during the run
        # to cleanup the label_mapping of unused values, example:
        # self._active_label_mapping = {
        #     'pod': {
        #         'dd-agent-9s1l1': True
        #     }
        # }
        config['_active_label_mapping'] = {}

        # `_watched_labels` holds the list of label to watch for enrichment
        config['_watched_labels'] = set()

        config['_dry_run'] = True

        # Some metrics are ignored because they are duplicates or introduce a
        # very high cardinality. Metrics included in this list will be silently
        # skipped without a 'Unable to handle metric' debug line in the logs
        config['ignore_metrics'] = []

        # If you want to send the buckets as tagged values when dealing with histograms,
        # set send_histograms_buckets to True, set to False otherwise.
        config['send_histograms_buckets'] = is_affirmative(instance.get('send_histograms_buckets',
                                                           default_instance.get('send_histograms_buckets', True)))

        # If you want to send `counter` metrics as monotonic counts, set this value to True.
        # Set to False if you want to instead send those metrics as `gauge`.
        config['send_monotonic_counter'] = is_affirmative(instance.get('send_monotonic_counter',
                                                          default_instance.get('send_monotonic_counter', True)))

        # If the `labels_mapper` dictionary is provided, the metrics labels names
        # in the `labels_mapper` will use the corresponding value as tag name
        # when sending the gauges.
        config['labels_mapper'] = default_instance.get('labels_mapper', {})
        config['labels_mapper'].update(instance.get('labels_mapper', {}))
        # Rename bucket "le" label to "upper_bound"
        config['labels_mapper']['le'] = 'upper_bound'

        # `exclude_labels` is an array of labels names to exclude. Those labels
        # will just not be added as tags when submitting the metric.
        config['exclude_labels'] = default_instance.get('exclude_labels', []) + instance.get('exclude_labels', [])

        # `type_overrides` is a dictionary where the keys are prometheus metric names
        # and the values are a metric type (name as string) to use instead of the one
        # listed in the payload. It can be used to force a type on untyped metrics.
        # Note: it is empty in the parent class but will need to be
        # overloaded/hardcoded in the final check not to be counted as custom metric.
        config['type_overrides'] = default_instance.get('type_overrides', {})
        config['type_overrides'].update(instance.get('type_overrides', {}))

        # Some metrics are retrieved from differents hosts and often
        # a label can hold this information, this transfers it to the hostname
        config['label_to_hostname'] = instance.get('label_to_hostname', default_instance.get('label_to_hostname', None))

        # In combination to label_as_hostname, allows to add a common suffix to the hostnames
        # submitted. This can be used for instance to discriminate hosts between clusters.
        config['label_to_hostname_suffix'] = instance.get('label_to_hostname_suffix', default_instance.get('label_to_hostname_suffix', None))


        # Add a 'health' service check for the prometheus endpoint
        config['health_service_check'] = is_affirmative(instance.get('health_service_check',
                                                        default_instance.get('health_service_check', True)))

        # Can either be only the path to the certificate and thus you should specify the private key
        # or it can be the path to a file containing both the certificate & the private key
        config['ssl_cert'] = instance.get('ssl_cert', default_instance.get('ssl_cert', None))

        # Needed if the certificate does not include the private key
        #
        # /!\ The private key to your local certificate must be unencrypted.
        # Currently, Requests does not support using encrypted keys.
        config['ssl_private_key'] = instance.get('ssl_private_key', default_instance.get('ssl_private_key', None))

        # The path to the trusted CA used for generating custom certificates
        config['ssl_ca_cert'] = instance.get('ssl_ca_cert', default_instance.get('ssl_ca_cert', None))

        # Extra http headers to be sent when polling endpoint
        config['extra_headers'] = default_instance.get('extra_headers', {})
        config['extra_headers'].update(instance.get('extra_headers', {}))

        # Timeout used during the network request
        config['prometheus_timeout'] = instance.get('prometheus_timeout', default_instance.get('prometheus_timeout', 10))

        # Authentication used when polling endpoint
        config['username'] = instance.get('username', default_instance.get('username', None))
        config['password'] = instance.get('password', default_instance.get('password', None))

        # Custom tags that will be sent with each metric
        config['custom_tags'] = instance.get('tags', [])

        # List of strings to filter the input text payload on. If any line contains
        # one of these strings, it will be filtered out before being parsed.
        # INTERNAL FEATURE, might be removed in future versions
        config['_text_filter_blacklist'] = []

        return config

    def parse_metric_family(self, response, scraper_config):
        """
        Parse the MetricFamily from a valid requests.Response object to provide a MetricFamily object (see [0])
        The text format uses iter_lines() generator.
        :param response: requests.Response
        :return: core.Metric
        """
        input_gen = response.iter_lines(chunk_size=self.REQUESTS_CHUNK_SIZE, decode_unicode=True)
        if scraper_config['_text_filter_blacklist']:
            input_gen = self._text_filter_input(input_gen, scraper_config)

        for metric in text_fd_to_metric_families(input_gen):
            metric.type = scraper_config['type_overrides'].get(metric.name, metric.type)
            if metric.type not in self.METRIC_TYPES:
                continue
            metric.name = self._remove_metric_prefix(metric.name, scraper_config)
            yield metric

    def _text_filter_input(self, input_gen, scraper_config):
        """
        Filters out the text input line by line to avoid parsing and processing
        metrics we know we don't want to process. This only works on `text/plain`
        payloads, and is an INTERNAL FEATURE implemented for the kubelet check
        :param input_get: line generator
        :output: generator of filtered lines
        """
        for line in input_gen:
            for item in scraper_config['_text_filter_blacklist']:
                if item in line:
                    break
            else:
                # No blacklist matches, passing the line through
                yield line

    def _remove_metric_prefix(self, metric, scraper_config):
        prometheus_metrics_prefix = scraper_config['prometheus_metrics_prefix']
        return metric[len(prometheus_metrics_prefix):] if metric.startswith(prometheus_metrics_prefix) else metric

    def scrape_metrics(self, scraper_config):
        """
        Poll the data from prometheus and return the metrics as a generator.
        """
        response = self.poll(scraper_config)
        try:
            # no dry run if no label joins
            if not scraper_config['label_joins']:
                scraper_config['_dry_run'] = False
            elif not scraper_config['_watched_labels']:
                # build the _watched_labels set
                for metric, val in iteritems(scraper_config['label_joins']):
                    scraper_config['_watched_labels'].add(val['label_to_match'])

            for metric in self.parse_metric_family(response, scraper_config):
                yield metric

            # Set dry run off
            scraper_config['_dry_run'] = False
            # Garbage collect unused mapping and reset active labels
            for metric, mapping in list(iteritems(scraper_config['_label_mapping'])):
                for key, val in list(iteritems(mapping)):
                    if key not in scraper_config['_active_label_mapping'][metric]:
                        del scraper_config['_label_mapping'][metric][key]
            scraper_config['_active_label_mapping'] = {}
        finally:
            response.close()

    def process(self, scraper_config, metric_transformers=None):
        """
        Polls the data from prometheus and pushes them as gauges
        `endpoint` is the metrics endpoint to use to poll metrics from Prometheus

        Note that if the instance has a 'tags' attribute, it will be pushed
        automatically as additional custom tags and added to the metrics
        """
        for metric in self.scrape_metrics(scraper_config):
            self.process_metric(metric, scraper_config, metric_transformers=metric_transformers)

    def _store_labels(self, metric, scraper_config):
        scraper_config['label_joins']
        # If targeted metric, store labels
        if metric.name in scraper_config['label_joins']:
            matching_label = scraper_config['label_joins'][metric.name]['label_to_match']
            for sample in metric.samples:
                labels_list = []
                matching_value = None
                for label_name, label_value in iteritems(sample[self.SAMPLE_LABELS]):
                    if label_name == matching_label:
                        matching_value = label_value
                    elif label_name in scraper_config['label_joins'][metric.name]['labels_to_get']:
                        labels_list.append((label_name, label_value))
                try:
                    scraper_config['_label_mapping'][matching_label][matching_value] = labels_list
                except KeyError:
                    if matching_value is not None:
                        scraper_config['_label_mapping'][matching_label] = {matching_value: labels_list}

    def _join_labels(self, metric, scraper_config):
        # Filter metric to see if we can enrich with joined labels
        if scraper_config['label_joins']:
            for sample in metric.samples:
                for label_name in scraper_config['_watched_labels'].intersection(set(sample[self.SAMPLE_LABELS].keys())):
                    # Set this label value as active
                    if label_name not in scraper_config['_active_label_mapping']:
                        scraper_config['_active_label_mapping'][label_name] = {}
                    scraper_config['_active_label_mapping'][label_name][sample[self.SAMPLE_LABELS][label_name]] = True
                    # If mapping found add corresponding labels
                    try:
                        for label_tuple in scraper_config['_label_mapping'][label_name][sample[self.SAMPLE_LABELS][label_name]]:
                            sample[self.SAMPLE_LABELS][label_tuple[0]] = label_tuple[1]
                    except KeyError:
                        pass

    def process_metric(self, metric, scraper_config, metric_transformers=None):
        """
        Handle a prometheus metric according to the following flow:
            - search scraper_config['metrics_mapper'] for a prometheus.metric <--> datadog.metric mapping
            - call check method with the same name as the metric
            - log some info if none of the above worked

        `metric_transformers` is a dict of <metric name>:<function to run when the metric name is encountered>
        """
        # If targeted metric, store labels
        self._store_labels(metric, scraper_config)

        if metric.name in scraper_config['ignore_metrics']:
            return  # Ignore the metric

        # Filter metric to see if we can enrich with joined labels
        self._join_labels(metric, scraper_config)

        if scraper_config['_dry_run']:
            return

        try:
            self._submit(scraper_config['metrics_mapper'][metric.name], metric, scraper_config)
        except KeyError:
            if metric_transformers is not None:
                if metric.name in metric_transformers:
                    try:
                        # Get the transformer function for this specific metric
                        transformer = metric_transformers[metric.name]
                        transformer(metric, scraper_config)
                    except Exception as err:
                        self.log.warning("Error handling metric: {} - error: {}".format(metric.name, err))
                else:
                    self.log.debug("Unable to handle metric: {0} - error: No handler function named '{0}' defined".format(metric.name))
            else:
                # build the wildcard list if first pass
                if scraper_config['_metrics_wildcards'] is None:
                    scraper_config['_metrics_wildcards'] = [x for x in scraper_config['metrics_mapper'] if '*' in x]

                # try matching wildcard (generic check)
                for wildcard in scraper_config['_metrics_wildcards']:
                    if fnmatchcase(metric.name, wildcard):
                        self._submit(metric.name, metric, scraper_config)

    def poll(self, scraper_config, headers=None):
        """
        Custom headers can be added to the default headers.

        Returns a valid requests.Response, raise requests.HTTPError if the status code of the requests.Response
        isn't valid - see response.raise_for_status()

        The caller needs to close the requests.Response

        :param endpoint: string url endpoint
        :param headers: extra headers
        :return: requests.Response
        """
        endpoint = scraper_config.get('prometheus_url')

        # Should we send a service check for when we make a request
        health_service_check = scraper_config['health_service_check']
        service_check_name = '{}{}'.format(scraper_config['namespace'], '.prometheus.health')
        service_check_tags = scraper_config['custom_tags'] + ['endpoint:' + endpoint]
        try:
            response = self.send_request(endpoint, scraper_config, headers)
        except requests.exceptions.SSLError:
            self.log.error("Invalid SSL settings for requesting {} endpoint".format(endpoint))
            raise
        except IOError:
            if health_service_check:
                self.service_check(
                    service_check_name,
                    AgentCheck.CRITICAL,
                    tags=service_check_tags
                )
            raise
        try:
            response.raise_for_status()
            if health_service_check:
                self.service_check(
                    service_check_name,
                    AgentCheck.OK,
                    tags=service_check_tags
                )
            return response
        except requests.HTTPError:
            response.close()
            if health_service_check:
                self.service_check(
                    service_check_name,
                    AgentCheck.CRITICAL,
                    tags=service_check_tags
                )
            raise

    def send_request(self, endpoint, scraper_config, headers=None):
        # Determine the headers
        if headers is None:
            headers = {}
        if 'accept-encoding' not in headers:
            headers['accept-encoding'] = 'gzip'
        headers.update(scraper_config['extra_headers'])

        # Determine the SSL verification settings
        cert = None
        if isinstance(scraper_config['ssl_cert'], string_types):
            if isinstance(scraper_config['ssl_private_key'], string_types):
                cert = (scraper_config['ssl_cert'], scraper_config['ssl_private_key'])
            else:
                cert = scraper_config['ssl_cert']
        verify = True
        if isinstance(scraper_config['ssl_ca_cert'], string_types):
            verify = scraper_config['ssl_ca_cert']
        elif scraper_config['ssl_ca_cert'] is False:
            disable_warnings(InsecureRequestWarning)
            verify = False

        # Determine the authentication settings
        username = scraper_config['username']
        password = scraper_config['password']
        auth = (username, password) if username is not None and password is not None else None

        return requests.get(endpoint, headers=headers, stream=True, timeout=scraper_config['prometheus_timeout'],
                            cert=cert, verify=verify, auth=auth)

    def _submit(self, metric_name, metric, scraper_config, hostname=None):
        """
        For each sample in the metric, report it as a gauge with all labels as tags
        except if a labels dict is passed, in which case keys are label names we'll extract
        and corresponding values are tag names we'll use (eg: {'node': 'node'}).

        Histograms generate a set of values instead of a unique metric.
        send_histograms_buckets is used to specify if yes or no you want to
            send the buckets as tagged values when dealing with histograms.

        `custom_tags` is an array of 'tag:value' that will be added to the
        metric when sending the gauge to Datadog.
        """
        if metric.type in ["gauge", "counter", "rate"]:
            metric_name_with_namespace = '{}.{}'.format(scraper_config['namespace'], metric_name)
            for sample in metric.samples:
                val = sample[self.SAMPLE_VALUE]
                if not self._is_value_valid(val):
                    self.log.debug("Metric value is not supported for metric {}".format(sample[self.SAMPLE_NAME]))
                    continue
                custom_hostname = self._get_hostname(hostname, sample, scraper_config)
                # Determine the tags to send
                tags = self._metric_tags(metric_name, val, sample, scraper_config, hostname=custom_hostname)
                if metric.type == "counter" and scraper_config['send_monotonic_counter']:
                    self.monotonic_count(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)
                elif metric.type == "rate":
                    self.rate(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)
                else:
                    self.gauge(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)
        elif metric.type == "histogram":
            self._submit_gauges_from_histogram(metric_name, metric, scraper_config)
        elif metric.type == "summary":
            self._submit_gauges_from_summary(metric_name, metric, scraper_config)
        else:
            self.log.error("Metric type {} unsupported for metric {}.".format(metric.type, metric_name))

    def _get_hostname(self, hostname, sample, scraper_config):
        """
        If hostname is None, look at label_to_hostname setting
        """
        if (hostname is None and scraper_config['label_to_hostname'] is not None and
                scraper_config['label_to_hostname'] in sample[self.SAMPLE_LABELS]):
                hostname = sample[self.SAMPLE_LABELS][scraper_config['label_to_hostname']]
                suffix = scraper_config['label_to_hostname_suffix']
                if suffix is not None:
                    hostname += suffix

        return hostname

    def _submit_gauges_from_summary(self, metric_name, metric, scraper_config, hostname=None):
        """
        Extracts metrics from a prometheus summary metric and sends them as gauges
        """
        for sample in metric.samples:
            val = sample[self.SAMPLE_VALUE]
            if not self._is_value_valid(val):
                self.log.debug("Metric value is not supported for metric {}".format(sample[self.SAMPLE_NAME]))
                continue
            custom_hostname = self._get_hostname(hostname, sample, scraper_config)
            if sample[self.SAMPLE_NAME].endswith("_sum"):
                tags = self._metric_tags(metric_name, val, sample, scraper_config, hostname=custom_hostname)
                self.gauge("{}.{}.sum".format(scraper_config['namespace'], metric_name), val, tags=tags, hostname=custom_hostname)
            elif sample[self.SAMPLE_NAME].endswith("_count"):
                tags = self._metric_tags(metric_name, val, sample, scraper_config, hostname=custom_hostname)
                self.gauge("{}.{}.count".format(scraper_config['namespace'], metric_name), val, tags=tags, hostname=custom_hostname)
            else:
                sample[self.SAMPLE_LABELS]["quantile"] = float(sample[self.SAMPLE_LABELS]["quantile"])
                tags = self._metric_tags(metric_name, val, sample, scraper_config, hostname=custom_hostname)
                self.gauge("{}.{}.quantile".format(scraper_config['namespace'], metric_name), val, tags=tags, hostname=custom_hostname)

    def _submit_gauges_from_histogram(self, metric_name, metric, scraper_config, hostname=None):
        """
        Extracts metrics from a prometheus histogram and sends them as gauges
        """
        for sample in metric.samples:
            val = sample[self.SAMPLE_VALUE]
            if not self._is_value_valid(val):
                self.log.debug("Metric value is not supported for metric {}".format(sample[self.SAMPLE_NAME]))
                continue
            custom_hostname = self._get_hostname(hostname, sample, scraper_config)
            if sample[self.SAMPLE_NAME].endswith("_sum"):
                tags = self._metric_tags(metric_name, val, sample, scraper_config, hostname)
                self.gauge("{}.{}.sum".format(scraper_config['namespace'], metric_name), val, tags=tags, hostname=custom_hostname)
            elif sample[self.SAMPLE_NAME].endswith("_count"):
                tags = self._metric_tags(metric_name, val, sample, scraper_config, hostname)
                self.gauge("{}.{}.count".format(scraper_config['namespace'], metric_name), val, tags=tags, hostname=custom_hostname)
            elif (scraper_config['send_histograms_buckets'] and sample[self.SAMPLE_NAME].endswith("_bucket") and
                    "Inf" not in sample[self.SAMPLE_LABELS]["le"]):
                sample[self.SAMPLE_LABELS]["le"] = float(sample[self.SAMPLE_LABELS]["le"])
                tags = self._metric_tags(metric_name, val, sample, scraper_config, hostname)
                self.gauge("{}.{}.count".format(scraper_config['namespace'], metric_name), val, tags=tags, hostname=custom_hostname)

    def _metric_tags(self, metric_name, val, sample, scraper_config, hostname=None):
        custom_tags = scraper_config['custom_tags']
        _tags = list(custom_tags)
        for label_name, label_value in iteritems(sample[self.SAMPLE_LABELS]):
            if label_name not in scraper_config['exclude_labels']:
                tag_name = scraper_config['labels_mapper'].get(label_name, label_name)
                _tags.append('{}:{}'.format(tag_name, label_value))
        return self._finalize_tags_to_submit(_tags, metric_name, val, sample, custom_tags=custom_tags, hostname=hostname)

    def _is_value_valid(self, val):
        return not (isnan(val) or isinf(val))
