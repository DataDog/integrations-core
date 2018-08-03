# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from fnmatch import fnmatchcase
from ...errors import CheckException
import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from collections import defaultdict
from google.protobuf.internal.decoder import _DecodeVarint32  # pylint: disable=E0611,E0401
from ...utils.prometheus import metrics_pb2
from math import isnan, isinf
from prometheus_client.parser import text_fd_to_metric_families

from six import PY3, iteritems, string_types

from ..base import AgentCheck

from datadog_checks.config import is_affirmative

if PY3:
    long = int


class PrometheusFormat:
    """
    Used to specify if you want to use the protobuf format or the text format when
    querying prometheus metrics
    """
    PROTOBUF = 'PROTOBUF'
    TEXT = 'TEXT'


class UnknownFormatError(TypeError):
    pass


class PrometheusScraperMixin(object):
    # pylint: disable=E1101
    # This class is not supposed to be used by itself, it provides scraping behavior but
    # need to be within a check in the end

    UNWANTED_LABELS = ['le', 'quantile']  # are specifics keys for prometheus itself
    REQUESTS_CHUNK_SIZE = 1024 * 10  # use 10kb as chunk size when using the Stream feature in requests.get

    def __init__(self, *args, **kwargs):
        # Initialize AgentCheck's base class
        super(PrometheusScraperMixin, self).__init__(*args, **kwargs)

        # message.type is the index in this array
        # see: https://github.com/prometheus/client_model/blob/master/ruby/lib/prometheus/client/model/metrics.pb.rb
        self.METRIC_TYPES = ['counter', 'gauge', 'summary', 'untyped', 'histogram']

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

        config['NAMESPACE'] = namespace

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

        # `rate_metrics` contains the metrics that should be sent as rates
        config['rate_metrics'] = self._extract_rate_metrics(default_instance.get('type_overrides', []))
        config['rate_metrics'].extend(self._extract_rate_metrics(instance.get('type_overrides', [])))

        # `_metrics_wildcards` holds the potential wildcards to match for metrics
        config['_metrics_wildcards'] = None

        # `prometheus_metrics_prefix` allows to specify a prefix that all
        # prometheus metrics should have. This can be used when the prometheus
        # endpoint we are scrapping allows to add a custom prefix to it's
        # metrics.
        config['prometheus_metrics_prefix'] = instance.get('prometheus_metrics_prefix', default_instance.get('prometheus_metrics_prefix', ''))

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
                                                          default_instance.get('send_monotonic_counter', False)))

        # If the `labels_mapper` dictionary is provided, the metrics labels names
        # in the `labels_mapper` will use the corresponding value as tag name
        # when sending the gauges.
        config['labels_mapper'] = default_instance.get('labels_mapper', {})
        config['labels_mapper'].update(instance.get('labels_mapper', {}))

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

        The protobuf format directly parse the response.content property searching for Prometheus messages of type
        MetricFamily [0] delimited by a varint32 [1] when the content-type is a `application/vnd.google.protobuf`.

        [0] https://github.com/prometheus/client_model/blob/086fe7ca28bde6cec2acd5223423c1475a362858/metrics.proto#L76-%20%20L81
        [1] https://developers.google.com/protocol-buffers/docs/reference/java/com/google/protobuf/AbstractMessageLite#writeDelimitedTo(java.io.OutputStream)

        :param response: requests.Response
        :return: metrics_pb2.MetricFamily()
        """
        if 'application/vnd.google.protobuf' in response.headers['Content-Type']:
            n = 0
            buf = response.content
            while n < len(buf):
                msg_len, new_pos = _DecodeVarint32(buf, n)
                n = new_pos
                msg_buf = buf[n:n+msg_len]
                n += msg_len

                message = metrics_pb2.MetricFamily()
                message.ParseFromString(msg_buf)
                message.name = self._remove_metric_prefix(message.name, scraper_config)

                # Lookup type overrides:
                if scraper_config['type_overrides'] and message.name in scraper_config['type_overrides']:
                    new_type = scraper_config['type_overrides'][message.name]
                    if new_type in self.METRIC_TYPES:
                        message.type = self.METRIC_TYPES.index(new_type)
                    else:
                        self.log.debug("type override %s for %s is not a valid type name" % (new_type, message.name))
                yield message

        elif 'text/plain' in response.headers['Content-Type']:
            input_gen = response.iter_lines(chunk_size=self.REQUESTS_CHUNK_SIZE)
            if scraper_config['_text_filter_blacklist']:
                input_gen = self._text_filter_input(input_gen, scraper_config)

            messages = defaultdict(list)  # map with the name of the element (before the labels)
            # and the list of occurrences with labels and values

            obj_map = {}  # map of the types of each metrics
            obj_help = {}  # help for the metrics
            for metric in text_fd_to_metric_families(input_gen):
                metric.name = self._remove_metric_prefix(metric.name, scraper_config)
                metric_name = '{}_bucket'.format(metric.name) if metric.type == 'histogram' else metric.name
                metric_type = scraper_config['type_overrides'].get(metric_name, metric.type)
                if metric_type == 'untyped' or metric_type not in self.METRIC_TYPES:
                    continue

                for sample in metric.samples:
                    if (sample[0].endswith('_sum') or sample[0].endswith('_count')) and \
                            metric_type in ['histogram', 'summary']:
                        messages[sample[0]].append({'labels': sample[1], 'value': sample[2]})
                    else:
                        messages[metric_name].append({'labels': sample[1], 'value': sample[2]})

                obj_map[metric.name] = metric_type
                obj_help[metric.name] = metric.documentation

            for _m in obj_map:
                if _m in messages or (obj_map[_m] == 'histogram' and ('{}_bucket'.format(_m) in messages)):
                    yield self._extract_metric_from_map(_m, messages, obj_map, obj_help)
        else:
            raise UnknownFormatError('Unsupported content-type provided: {}'.format(
                response.headers['Content-Type']))

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

    @staticmethod
    def get_metric_value_by_labels(messages, _metric, _m, metric_suffix):
        """
        :param messages: dictionary as metric_name: {labels: {}, value: 10}
        :param _metric: dictionary as {labels: {le: '0.001', 'custom': 'value'}}
        :param _m: str as metric name
        :param metric_suffix: str must be in (count or sum)
        :return: value of the metric_name matched by the labels
        """
        metric_name = '{}_{}'.format(_m, metric_suffix)
        expected_labels = set([(k, v) for k, v in iteritems(_metric["labels"])
                               if k not in PrometheusScraperMixin.UNWANTED_LABELS])
        for elt in messages[metric_name]:
            current_labels = set([(k, v) for k, v in iteritems(elt["labels"])
                                  if k not in PrometheusScraperMixin.UNWANTED_LABELS])
            # As we have two hashable objects we can compare them without any side effects
            if current_labels == expected_labels:
                return float(elt['value'])

        raise AttributeError("cannot find expected labels for metric {} with suffix {}".format(metric_name, metric_suffix))

    def _extract_rate_metrics(self, type_overrides):
        rate_metrics = []
        for metric in type_overrides:
            if type_overrides[metric] == 'rate':
                rate_metrics.append(metric)
                type_overrides[metric] = 'gauge'
        return rate_metrics

    def _extract_metric_from_map(self, _m, messages, obj_map, obj_help):
        """
        Extracts MetricFamily objects from the maps generated by parsing the
        strings in _extract_metrics_from_string
        """
        _obj = metrics_pb2.MetricFamily()
        _obj.name = _m
        _obj.type = self.METRIC_TYPES.index(obj_map[_m])
        if _m in obj_help:
            _obj.help = obj_help[_m]
        # trick for histograms
        _newlbl = _m
        if obj_map[_m] == 'histogram':
            _newlbl = '{}_bucket'.format(_m)
        # Loop through the array of metrics ({labels, value}) built earlier
        for _metric in messages[_newlbl]:
            # in the case of quantiles and buckets, they need to be grouped by labels
            if obj_map[_m] in ['summary', 'histogram'] and len(_obj.metric) > 0:
                _label_exists = False
                _metric_minus = {k: v for k, v in list(iteritems(_metric['labels'])) if k not in ['quantile', 'le']}
                _metric_idx = 0
                for mls in _obj.metric:
                    _tmp_lbl = {idx.name: idx.value for idx in mls.label}
                    if _metric_minus == _tmp_lbl:
                        _label_exists = True
                        break
                    _metric_idx = _metric_idx + 1
                if _label_exists:
                    _g = _obj.metric[_metric_idx]
                else:
                    _g = _obj.metric.add()
            else:
                _g = _obj.metric.add()
            if obj_map[_m] == 'counter':
                _g.counter.value = float(_metric['value'])
            elif obj_map[_m] == 'gauge':
                _g.gauge.value = float(_metric['value'])
            elif obj_map[_m] == 'summary':
                if '{}_count'.format(_m) in messages:
                    _g.summary.sample_count = long(self.get_metric_value_by_labels(messages, _metric, _m, 'count'))
                if '{}_sum'.format(_m) in messages:
                    _g.summary.sample_sum = self.get_metric_value_by_labels(messages, _metric, _m, 'sum')
            # TODO: see what can be done with the untyped metrics
            elif obj_map[_m] == 'histogram':
                if '{}_count'.format(_m) in messages:
                    _g.histogram.sample_count = long(self.get_metric_value_by_labels(messages, _metric, _m, 'count'))
                if '{}_sum'.format(_m) in messages:
                    _g.histogram.sample_sum = self.get_metric_value_by_labels(messages, _metric, _m, 'sum')
            # last_metric = len(_obj.metric) - 1
            # if last_metric >= 0:
            for lbl in _metric['labels']:
                # In the string format, the quantiles are in the labels
                if lbl == 'quantile':
                    # _q = _obj.metric[last_metric].summary.quantile.add()
                    _q = _g.summary.quantile.add()
                    _q.quantile = float(_metric['labels'][lbl])
                    _q.value = float(_metric['value'])
                # The upper_bounds are stored as "le" labels on string format
                elif obj_map[_m] == 'histogram' and lbl == 'le':
                    # _q = _obj.metric[last_metric].histogram.bucket.add()
                    _q = _g.histogram.bucket.add()
                    _q.upper_bound = float(_metric['labels'][lbl])
                    _q.cumulative_count = long(float(_metric['value']))
                else:
                    # labels deduplication
                    is_in_labels = False
                    for _existing_lbl in _g.label:
                        if lbl == _existing_lbl.name:
                            is_in_labels = True
                    if not is_in_labels:
                        _l = _g.label.add()
                        _l.name = lbl
                        _l.value = _metric['labels'][lbl]
        return _obj

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
            for metric, mapping in scraper_config['_label_mapping'].items():
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

    def _store_labels(self, message, scraper_config):
        # If targeted metric, store labels
        if message.name in scraper_config['label_joins']:
            matching_label = scraper_config['label_joins'][message.name]['label_to_match']
            for metric in message.metric:
                labels_list = []
                matching_value = None
                for label in metric.label:
                    if label.name == matching_label:
                        matching_value = label.value
                    elif label.name in scraper_config['label_joins'][message.name]['labels_to_get']:
                        labels_list.append((label.name, label.value))
                try:
                    scraper_config['_label_mapping'][matching_label][matching_value] = labels_list
                except KeyError:
                    if matching_value is not None:
                        scraper_config['_label_mapping'][matching_label] = {matching_value: labels_list}

    def _join_labels(self, message, scraper_config):
        # Filter metric to see if we can enrich with joined labels
        if scraper_config['label_joins']:
            for metric in message.metric:
                for label in metric.label:
                    if label.name in scraper_config['_watched_labels']:
                        # Set this label value as active
                        if label.name not in scraper_config['_active_label_mapping']:
                            scraper_config['_active_label_mapping'][label.name] = {}
                        scraper_config['_active_label_mapping'][label.name][label.value] = True
                        # If mapping found add corresponding labels
                        try:
                            for label_tuple in scraper_config['_label_mapping'][label.name][label.value]:
                                extra_label = metric.label.add()
                                extra_label.name, extra_label.value = label_tuple
                        except KeyError:
                            pass

    def process_metric(self, message, scraper_config, metric_transformers=None):
        """
        Handle a prometheus metric message according to the following flow:
            - search scraper_config['metrics_mapper'] for a prometheus.metric <--> datadog.metric mapping
            - call check method with the same name as the metric
            - log some info if none of the above worked

        `metric_transformers` fix me
        """
        # If targeted metric, store labels
        self._store_labels(message, scraper_config)

        if message.name in scraper_config['ignore_metrics']:
            return  # Ignore the metric

        # Filter metric to see if we can enrich with joined labels
        self._join_labels(message, scraper_config)

        if scraper_config['_dry_run']:
            return

        try:
            metric = scraper_config['metrics_mapper'][message.name]
            self._submit(metric, message, scraper_config)
        except KeyError:
            if metric_transformers is not None:
                if message.name in metric_transformers:
                    #try:
                        # Get the transformer function for this specific metric
                        transformer = metric_transformers[message.name]
                        transformer(message, scraper_config)
                    #except Exception as err:
                    #    self.log.warning("Error handling metric: {} - error: {}".format(message.name, err))
                else:
                    self.log.debug("Unable to handle metric: {0} - error: No handler function named '{0}' defined".format(message.name))
            else:
                # build the wildcard list if first pass
                if scraper_config['_metrics_wildcards'] is None:
                    scraper_config['_metrics_wildcards'] = [x for x in scraper_config['metrics_mapper'].keys() if '*' in x]

                # try matching wildcard (generic check)
                for wildcard in scraper_config['_metrics_wildcards']:
                    if fnmatchcase(message.name, wildcard):
                        self._submit(message.name, message, scraper_config)

    def poll(self, scraper_config, pFormat=PrometheusFormat.PROTOBUF, headers=None):
        """
        Polls the metrics from the prometheus metrics endpoint provided.
        Defaults to the protobuf format, but can use the formats specified by
        the PrometheusFormat class.
        Custom headers can be added to the default headers.

        Returns a valid requests.Response, raise requests.HTTPError if the status code of the requests.Response
        isn't valid - see response.raise_for_status()

        The caller needs to close the requests.Response

        :param endpoint: string url endpoint
        :param pFormat: the preferred format defined in PrometheusFormat
        :param headers: extra headers
        :return: requests.Response
        """
        endpoint = scraper_config.get('prometheus_url')

        # Should we send a service check for when we make a request
        health_service_check = scraper_config['health_service_check']
        service_check_name = '{}{}'.format(scraper_config['NAMESPACE'], '.prometheus.health')
        service_check_tags = scraper_config['custom_tags'] + ['endpoint:' + endpoint]
        try:
            response = self.send_request(endpoint, scraper_config, pFormat, headers)
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

    def send_request(self, endpoint, scraper_config, pFormat=PrometheusFormat.PROTOBUF, headers=None):
        # Determine the headers
        if headers is None:
            headers = {}
        if 'accept-encoding' not in headers:
            headers['accept-encoding'] = 'gzip'
        if pFormat == PrometheusFormat.PROTOBUF:
            headers['accept'] = 'application/vnd.google.protobuf; ' \
                                'proto=io.prometheus.client.MetricFamily; ' \
                                'encoding=delimited'
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

        return requests.get(endpoint, headers=headers, stream=False, timeout=scraper_config['prometheus_timeout'],
                            cert=cert, verify=verify, auth=auth)

    def _submit(self, metric_name, message, scraper_config, hostname=None):
        """
        For each metric in the message, report it as a gauge with all labels as tags
        except if a labels dict is passed, in which case keys are label names we'll extract
        and corresponding values are tag names we'll use (eg: {'node': 'node'}).

        Histograms generate a set of values instead of a unique metric.
        send_histograms_buckets is used to specify if yes or no you want to
            send the buckets as tagged values when dealing with histograms.

        `custom_tags` is an array of 'tag:value' that will be added to the
        metric when sending the gauge to Datadog.
        """
        if message.type < len(self.METRIC_TYPES):
            for metric in message.metric:
                custom_hostname = self._get_hostname(hostname, metric, scraper_config)
                if message.type == 0:
                    val = getattr(metric, self.METRIC_TYPES[message.type]).value
                    if self._is_value_valid(val):
                        # Determine the tags to send
                        tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname=custom_hostname)
                        metric_name_with_namespace = '{}.{}'.format(scraper_config['NAMESPACE'], metric_name)
                        if scraper_config['send_monotonic_counter']:
                            self.monotonic_count(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)
                        else:
                            self.gauge(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)
                    else:
                        self.log.debug("Metric value is not supported for metric {}.".format(metric_name))
                elif message.type == 4:
                    self._submit_gauges_from_histogram(metric_name, metric, scraper_config, hostname=custom_hostname)
                elif message.type == 2:
                    self._submit_gauges_from_summary(metric_name, metric, scraper_config, hostname=custom_hostname)
                else:
                    val = getattr(metric, self.METRIC_TYPES[message.type]).value
                    if self._is_value_valid(val):
                        tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname=custom_hostname)
                        metric_name_with_namespace = '{}.{}'.format(scraper_config['NAMESPACE'], metric_name)
                        if message.name in scraper_config['rate_metrics']:
                            self.rate(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)
                        else:
                            self.gauge(metric_name_with_namespace, val, tags=tags, hostname=custom_hostname)
                    else:
                        self.log.debug("Metric value is not supported for metric {}.".format(metric_name))
        else:
            self.log.error("Metric type {} unsupported for metric {}.".format(message.type, message.name))

    def _get_hostname(self, hostname, metric, scraper_config):
        """
        If hostname is None, look at label_to_hostname setting
        """
        if hostname is None and scraper_config['label_to_hostname'] is not None:
            for label in metric.label:
                if label.name == scraper_config['label_to_hostname']:
                    return label.value

        return hostname

    def _submit_gauges_from_summary(self, metric_name, metric, scraper_config, hostname=None):
        """
        Extracts metrics from a prometheus summary metric and sends them as gauges
        """
        # summaries do not have a value attribute
        val = getattr(metric, self.METRIC_TYPES[2]).sample_count
        if self._is_value_valid(val):
            tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname)
            self.gauge('{}.{}.count'.format(scraper_config['NAMESPACE'], metric_name), val, tags=tags, hostname=hostname)
        else:
            self.log.debug("Metric value is not supported for metric {}.count.".format(metric_name))
        val = getattr(metric, self.METRIC_TYPES[2]).sample_sum
        if self._is_value_valid(val):
            tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname=hostname)
            self.gauge('{}.{}.sum'.format(scraper_config['NAMESPACE'], metric_name), val, tags=tags, hostname=hostname)
        else:
            self.log.debug("Metric value is not supported for metric {}.sum.".format(metric_name))
        for quantile in getattr(metric, self.METRIC_TYPES[2]).quantile:
            val = quantile.value
            limit = quantile.quantile
            if self._is_value_valid(val):
                tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname=hostname) + ['quantile:{}'.format(limit)]
                self.gauge('{}.{}.quantile'.format(scraper_config['NAMESPACE'], metric_name), val, tags=tags, hostname=hostname)
            else:
                self.log.debug("Metric value is not supported for metric {}.quantile.".format(metric_name))

    def _submit_gauges_from_histogram(self, metric_name, metric, scraper_config, hostname=None):
        """
        Extracts metrics from a prometheus histogram and sends them as gauges
        """
        # histograms do not have a value attribute
        val = getattr(metric, self.METRIC_TYPES[4]).sample_count
        if self._is_value_valid(val):
            tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname=hostname)
            self.gauge('{}.{}.count'.format(scraper_config['NAMESPACE'], metric_name), val, tags=tags, hostname=hostname)
        else:
            self.log.debug("Metric value is not supported for metric {}.count.".format(metric_name))
        val = getattr(metric, self.METRIC_TYPES[4]).sample_sum
        if self._is_value_valid(val):
            tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname=hostname)
            self.gauge('{}.{}.sum'.format(scraper_config['NAMESPACE'], metric_name), val, tags=tags, hostname=hostname)
        else:
            self.log.debug("Metric value is not supported for metric {}.sum.".format(metric_name))
        if scraper_config['send_histograms_buckets']:
            for bucket in getattr(metric, self.METRIC_TYPES[4]).bucket:
                val = bucket.cumulative_count
                limit = bucket.upper_bound
                if self._is_value_valid(val):
                    tags = self._metric_tags(metric_name, val, metric, scraper_config, hostname=hostname) + ['upper_bound:{}'.format(limit)]
                    self.gauge('{}.{}.count'.format(scraper_config['NAMESPACE'], metric_name), val, tags=tags, hostname=hostname)
                else:
                    self.log.debug("Metric value is not supported for metric {}.count.".format(metric_name))

    def _metric_tags(self, metric_name, val, metric, scraper_config, hostname=None):
        custom_tags = scraper_config['custom_tags']
        _tags = list(custom_tags)
        for label in metric.label:
            if label.name not in scraper_config['exclude_labels']:
                tag_name = label.name
                if label.name in scraper_config['labels_mapper']:
                    tag_name = scraper_config['labels_mapper'][label.name]
                _tags.append('{}:{}'.format(tag_name, label.value))
        return self._finalize_tags_to_submit(_tags, metric_name, val, metric, custom_tags=custom_tags, hostname=hostname)

    def _is_value_valid(self, val):
        return not (isnan(val) or isinf(val))
