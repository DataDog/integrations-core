# (C) Datadog, Inc. 2013-present
# (C) Brett Langdon <brett@blangdon.com> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import time
from collections import defaultdict

from requests.exceptions import RequestException
from six import iteritems
from six.moves.urllib.parse import quote_plus, urljoin, urlparse

from datadog_checks.base import AgentCheck, is_affirmative, to_native_string

from .const import (
    ALERT_THRESHOLD,
    ATTRIBUTES,
    CONNECTION_TYPE,
    EVENT_TYPE,
    EXCHANGE_TYPE,
    MAX_DETAILED_EXCHANGES,
    MAX_DETAILED_NODES,
    MAX_DETAILED_QUEUES,
    METRIC_SUFFIX,
    NODE_TYPE,
    OVERVIEW_TYPE,
    QUEUE_TYPE,
    SOURCE_TYPE_NAME,
    TAG_PREFIX,
    TAGS_MAP,
    RabbitMQException,
)


class RabbitMQManagement(AgentCheck):
    """This check is for gathering statistics from the RabbitMQ
    Management Plugin (http://www.rabbitmq.com/management.html)
    """

    HTTP_CONFIG_REMAPPER = {
        'rabbitmq_user': {'name': 'username'},
        'rabbitmq_pass': {'name': 'password'},
        'ssl_verify': {'name': 'tls_verify'},
        'ignore_ssl_warning': {'name': 'tls_ignore_warning'},
        'use_legacy_auth_encoding': {'name': 'use_legacy_auth_encoding', 'default': False},
    }

    def __init__(self, name, init_config, instances=None):
        super(RabbitMQManagement, self).__init__(name, init_config, instances)
        self.already_alerted = []
        self.cached_vhosts = {}  # this is used to send CRITICAL rabbitmq.aliveness check if the server goes down

    def _get_config(self, instance):
        # make sure 'rabbitmq_api_url' is present and get parameters
        base_url = instance.get('rabbitmq_api_url', None)
        if not base_url:
            raise Exception('Missing "rabbitmq_api_url" in RabbitMQ config.')
        if not base_url.endswith('/'):
            base_url += '/'

        collect_nodes = is_affirmative(instance.get('collect_node_metrics', True))
        custom_tags = instance.get('tags', [])
        parsed_url = urlparse(base_url)
        if not parsed_url.scheme or "://" not in parsed_url.geturl():
            self.log.warning('The rabbit url did not include a protocol, assuming http')
            # urljoin cannot add a protocol to the rest of the url for some reason.
            # This still leaves the potential for errors, but such urls would never have been valid, either
            # and it's not likely to be useful to attempt to catch all possible mistakes people could make.
            # urlparse also has a known issue parsing url with no schema, but a port in the host section
            # mistakingly taking the host for the schema, hence the additional validation
            base_url = 'http://' + base_url
            parsed_url = urlparse(base_url)

        # Limit of queues/nodes to collect metrics from
        max_detailed = {
            EXCHANGE_TYPE: int(instance.get('max_detailed_exchanges', MAX_DETAILED_EXCHANGES)),
            QUEUE_TYPE: int(instance.get('max_detailed_queues', MAX_DETAILED_QUEUES)),
            NODE_TYPE: int(instance.get('max_detailed_nodes', MAX_DETAILED_NODES)),
        }

        # List of queues/nodes to collect metrics from
        specified = {
            EXCHANGE_TYPE: {
                'explicit': instance.get('exchanges', []),
                'regexes': instance.get('exchanges_regexes', []),
            },
            QUEUE_TYPE: {'explicit': instance.get('queues', []), 'regexes': instance.get('queues_regexes', [])},
            NODE_TYPE: {'explicit': instance.get('nodes', []), 'regexes': instance.get('nodes_regexes', [])},
        }

        for object_type, filters in iteritems(specified):
            for _, filter_objects in iteritems(filters):
                if type(filter_objects) != list:
                    raise TypeError("{0} / {0}_regexes parameter must be a list".format(object_type))

        return base_url, max_detailed, specified, custom_tags, collect_nodes

    def _collect_metadata(self, overview_response):
        version = to_native_string(overview_response['rabbitmq_version'])
        if version:
            # Rabbit versions follow semantic versioning https://www.rabbitmq.com/changelog.html
            self.set_metadata('version', version)
            self.log.debug("found rabbitmq version %s", version)
        else:
            self.log.warning("could not retrieve rabbitmq version information")

    def _get_vhosts(self, instance, base_url):
        vhosts = instance.get('vhosts')

        if not vhosts:
            # Fetch a list of _all_ vhosts from the API.
            vhosts_url = urljoin(base_url, 'vhosts')
            vhosts_response = self._get_data(vhosts_url)
            vhosts = [v['name'] for v in vhosts_response]

        return vhosts

    def check(self, instance):
        base_url, max_detailed, specified, custom_tags, collect_node_metrics = self._get_config(instance)
        try:
            vhosts = self._get_vhosts(instance, base_url)
            self.cached_vhosts[base_url] = vhosts
            limit_vhosts = []
            if self._limit_vhosts(instance):
                limit_vhosts = vhosts

            self.get_overview_stats(base_url, custom_tags)

            # Generate metrics from the status API.
            self.get_stats(
                instance,
                base_url,
                EXCHANGE_TYPE,
                max_detailed[EXCHANGE_TYPE],
                specified[EXCHANGE_TYPE],
                limit_vhosts,
                custom_tags,
            )
            self.get_stats(
                instance,
                base_url,
                QUEUE_TYPE,
                max_detailed[QUEUE_TYPE],
                specified[QUEUE_TYPE],
                limit_vhosts,
                custom_tags,
            )
            if collect_node_metrics:
                self.get_stats(
                    instance,
                    base_url,
                    NODE_TYPE,
                    max_detailed[NODE_TYPE],
                    specified[NODE_TYPE],
                    limit_vhosts,
                    custom_tags,
                )

            self.get_connections_stat(instance, base_url, CONNECTION_TYPE, vhosts, limit_vhosts, custom_tags)

            # Generate a service check from the aliveness API. In the case of an invalid response
            # code or unparsable JSON this check will send no data.
            self._check_aliveness(base_url, vhosts, custom_tags)

            # Generate a service check for the service status.
            self.service_check('rabbitmq.status', AgentCheck.OK, custom_tags)

        except RabbitMQException as e:
            msg = "Error executing check: {}".format(e)
            self.service_check('rabbitmq.status', AgentCheck.CRITICAL, custom_tags, message=msg)
            self.log.error(msg)

            # tag every vhost as CRITICAL or they would keep the latest value, OK, in case the RabbitMQ server goes down
            msg = "error while contacting rabbitmq ({}), setting aliveness to CRITICAL for vhosts: {}".format(
                base_url, self.cached_vhosts
            )
            self.log.error(msg)
            for vhost in self.cached_vhosts.get(base_url, []):
                self.service_check(
                    'rabbitmq.aliveness',
                    AgentCheck.CRITICAL,
                    ['vhost:{}'.format(vhost)] + custom_tags,
                    message="Could not contact aliveness API",
                )

    def _get_data(self, url):
        try:
            r = self.http.get(url)
            r.raise_for_status()
            return r.json()
        except RequestException as e:
            raise RabbitMQException('Cannot open RabbitMQ API url: {} {}'.format(url, str(e)))
        except ValueError as e:
            raise RabbitMQException('Cannot parse JSON response from API url: {} {}'.format(url, str(e)))

    def _filter_list(self, data, explicit_filters, regex_filters, object_type, tag_families):
        if explicit_filters or regex_filters:
            matching_lines = []
            for data_line in data:
                name = data_line.get("name")
                if name in explicit_filters:
                    matching_lines.append(data_line)
                    explicit_filters.remove(name)
                    continue

                match_found = self._append_match_lines(
                    regex_filters, name, tag_families, data_line, object_type, matching_lines
                )

                if match_found:
                    continue

                # Absolute names work only for queues and exchanges
                if object_type != QUEUE_TYPE and object_type != EXCHANGE_TYPE:
                    continue
                absolute_name = '{}/{}'.format(data_line.get("vhost"), name)
                if absolute_name in explicit_filters:
                    matching_lines.append(data_line)
                    explicit_filters.remove(absolute_name)
                    continue

                match_found = self._append_match_lines(
                    regex_filters, absolute_name, tag_families, data_line, object_type, matching_lines
                )
                if match_found:
                    continue
            return matching_lines
        return data

    def _append_match_lines(self, regex_filters, name, tag_families, data_line, object_type, matching_lines):
        result = False
        object_tag_name = "queue_family"
        if object_type == EXCHANGE_TYPE:
            object_tag_name = "exchange_family"
        for p in regex_filters:
            match = re.search(p, name)
            if match:
                if is_affirmative(tag_families) and match.groups():
                    named_groups_dict = match.groupdict()
                    if len(named_groups_dict) > 0:
                        for key in named_groups_dict:
                            key_name = object_tag_name + "_" + key
                            data_line[key] = named_groups_dict[key]
                            TAGS_MAP[object_type][key] = key_name
                    else:
                        data_line[object_tag_name] = match.groups()[0]
                matching_lines.append(data_line)
                result = True
                break
        return result

    def _get_tags(self, data, object_type, custom_tags):
        tags = []
        tag_list = TAGS_MAP[object_type]
        for t in tag_list:
            tag = data.get(t)
            if tag:
                # FIXME 8.x: remove this suffix or unify (sc doesn't have it)
                tags.append('{}_{}:{}'.format(TAG_PREFIX, tag_list[t], tag))
        return tags + custom_tags

    def _get_object_data(self, instance, base_url, object_type, limit_vhosts):
        """data is a list of nodes or queues:
        data = [
            {
                'status': 'running',
                'node': 'rabbit@host',
                'name': 'queue1',
                'consumers': 0,
                'vhost': '/',
                'backing_queue_status': {
                    'q1': 0,
                    'q3': 0,
                    'q2': 0,
                    'q4': 0,
                    'avg_ack_egress_rate': 0.0,
                    'ram_msg_count': 0,
                    'ram_ack_count': 0,
                    'len': 0,
                    'persistent_count': 0,
                    'target_ram_count': 'infinity',
                    'next_seq_id': 0,
                    'delta': ['delta', 'undefined', 0, 'undefined'],
                    'pending_acks': 0,
                    'avg_ack_ingress_rate': 0.0,
                    'avg_egress_rate': 0.0,
                    'avg_ingress_rate': 0.0
                },
                'durable': True,
                'idle_since': '2013-10-03 13:38:18',
                'exclusive_consumer_tag': '',
                'arguments': {},
                'memory': 10956,
                'policy': '',
                'auto_delete': False
            },
            {
                'status': 'running',
                'node': 'rabbit@host,
                'name': 'queue10',
                'consumers': 0,
                'vhost': '/',
                'backing_queue_status': {
                    'q1': 0,
                    'q3': 0,
                    'q2': 0,
                    'q4': 0,
                    'avg_ack_egress_rate': 0.0,
                    'ram_msg_count': 0,
                    'ram_ack_count': 0,
                    'len': 0,
                    'persistent_count': 0,
                    'target_ram_count': 'infinity',
                    'next_seq_id': 0,
                    'delta': ['delta', 'undefined', 0, 'undefined'],
                    'pending_acks': 0,
                    'avg_ack_ingress_rate': 0.0,
                    'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0
                },
                'durable': True,
                'idle_since': '2013-10-03 13:38:18',
                'exclusive_consumer_tag': '',
                'arguments': {},
                'memory': 10956,
                'policy': '',
                'auto_delete': False
            },
            {
                'status': 'running',
                'node': 'rabbit@host',
                'name': 'queue11',
                'consumers': 0,
                'vhost': '/',
                'backing_queue_status': {
                    'q1': 0,
                    'q3': 0,
                    'q2': 0,
                    'q4': 0,
                    'avg_ack_egress_rate': 0.0,
                    'ram_msg_count': 0,
                    'ram_ack_count': 0,
                    'len': 0,
                    'persistent_count': 0,
                    'target_ram_count': 'infinity',
                    'next_seq_id': 0,
                    'delta': ['delta', 'undefined', 0, 'undefined'],
                    'pending_acks': 0,
                    'avg_ack_ingress_rate': 0.0,
                    'avg_egress_rate': 0.0,
                    'avg_ingress_rate': 0.0
                },
                'durable': True,
                'idle_since': '2013-10-03 13:38:18',
                'exclusive_consumer_tag': '',
                'arguments': {},
                'memory': 10956,
                'policy': '',
                'auto_delete': False
            },
            ...
        ]
        """
        data = []

        # only do this if vhosts were specified,
        # otherwise it'll just be making more queries for the same data
        if self._limit_vhosts(instance) and object_type == QUEUE_TYPE:
            for vhost in limit_vhosts:
                url = '{}/{}'.format(object_type, quote_plus(vhost))
                try:
                    data += self._get_data(urljoin(base_url, url))
                except Exception as e:
                    self.log.debug("Couldn't grab queue data from vhost, %s: %s", vhost, e)
        else:
            data = self._get_data(urljoin(base_url, object_type))
        return data

    def get_stats(self, instance, base_url, object_type, max_detailed, filters, limit_vhosts, custom_tags):
        """
        instance: the check instance
        base_url: the url of the rabbitmq management api (e.g. http://localhost:15672/api)
        object_type: either QUEUE_TYPE or NODE_TYPE or EXCHANGE_TYPE
        max_detailed: the limit of objects to collect for this type
        filters: explicit or regexes filters of specified queues or nodes (specified in the yaml file)
        limit_vhosts: collection of vhosts to limit to
        custom_tags: Custom tags to get applied to all metrics
        """
        # Make a copy of this list as we will remove items from it at each
        # iteration
        explicit_filters = list(filters['explicit'])
        regex_filters = filters['regexes']
        data = self._get_object_data(instance, base_url, object_type, limit_vhosts)

        if len(explicit_filters) > max_detailed:
            raise Exception("The maximum number of {} you can specify is {}.".format(object_type, max_detailed))

        # a list of queues/nodes is specified. We process only those
        data = self._filter_list(
            data, explicit_filters, regex_filters, object_type, instance.get("tag_families", False)
        )

        # if no filters are specified, check everything according to the limits
        if len(data) > ALERT_THRESHOLD * max_detailed:
            # Post a message on the dogweb stream to warn
            self.alert(base_url, max_detailed, len(data), object_type, custom_tags)

        data_lines_sent = 0
        for data_line in data:
            if data_lines_sent >= max_detailed:
                # Display a warning in the info page
                msg = (
                    "Too many items to fetch. "
                    "You must choose the {} you are interested in by editing the rabbitmq.d/conf.yaml configuration "
                    "file or get in touch with Datadog support"
                ).format(object_type)
                self.warning(msg)
                break
            # We truncate the list if it's above the limit
            metrics_sent = self._get_metrics(data_line, object_type, custom_tags)
            if metrics_sent >= 1:
                data_lines_sent += 1

        # get a list of the number of bindings on a given queue
        # /api/queues/vhost/name/bindings
        if object_type is QUEUE_TYPE:
            self._get_queue_bindings_metrics(base_url, custom_tags, data, object_type)

    def get_overview_stats(self, base_url, custom_tags):
        data = self._get_data(urljoin(base_url, "overview"))
        self._collect_metadata(data)
        self._get_metrics(data, OVERVIEW_TYPE, custom_tags)

    def _get_metrics(self, data, object_type, custom_tags):
        tags = self._get_tags(data, object_type, custom_tags)
        metrics_sent = 0
        for attribute, metric_name, operation in ATTRIBUTES[object_type]:
            # Walk down through the data path, e.g. foo/bar => d['foo']['bar']
            root = data
            keys = attribute.split('/')

            # In RabbitMQ 3.1.x queue_totals is an empty list instead of a dict when initialising
            for path in keys[:-1]:
                if not isinstance(root, dict):
                    break
                root = root.get(path, {})
            value = root.get(keys[-1], None) if isinstance(root, dict) else None

            if value is not None:
                try:
                    self.gauge(
                        'rabbitmq.{}.{}'.format(METRIC_SUFFIX[object_type], metric_name), operation(value), tags=tags
                    )
                    metrics_sent += 1
                except ValueError:
                    self.log.debug(
                        "Caught ValueError for %s %s = %s  with tags: %s",
                        METRIC_SUFFIX[object_type],
                        attribute,
                        value,
                        tags,
                    )
        return metrics_sent

    def _get_queue_bindings_metrics(self, base_url, custom_tags, data, object_type):
        for item in data:
            vhost = item['vhost']
            tags = self._get_tags(item, object_type, custom_tags)
            url = '{}/{}/{}/bindings'.format(QUEUE_TYPE, quote_plus(vhost), quote_plus(item['name']))
            bindings_count = len(self._get_data(urljoin(base_url, url)))

            self.gauge('rabbitmq.queue.bindings.count', bindings_count, tags)

    def get_connections_stat(self, instance, base_url, object_type, vhosts, limit_vhosts, custom_tags):
        """
        Collect metrics on currently open connection per vhost.
        """
        grab_all_data = True

        if self._limit_vhosts(instance):
            grab_all_data = False
            data = []
            for vhost in vhosts:
                url = "vhosts/{}/{}".format(quote_plus(vhost), object_type)
                try:
                    data += self._get_data(urljoin(base_url, url))
                except Exception as e:
                    # This will happen if there is no connection data to grab
                    self.log.debug("Couldn't grab connection data from vhost, %s: %s", vhost, e)

        # sometimes it seems to need to fall back to this
        if grab_all_data or not len(data):
            data = self._get_data(urljoin(base_url, object_type))

        stats = {vhost: 0 for vhost in vhosts}
        connection_states = defaultdict(int)
        for conn in data:
            if conn['vhost'] in vhosts:
                stats[conn['vhost']] += 1
                # 'state' does not exist for direct type connections.
                connection_states[conn.get('state', 'direct')] += 1

        for vhost, nb_conn in iteritems(stats):
            self.gauge('rabbitmq.connections', nb_conn, tags=['{}_vhost:{}'.format(TAG_PREFIX, vhost)] + custom_tags)

        for conn_state, nb_conn in iteritems(connection_states):
            self.gauge(
                'rabbitmq.connections.state',
                nb_conn,
                tags=['{}_conn_state:{}'.format(TAG_PREFIX, conn_state)] + custom_tags,
            )

    def alert(self, base_url, max_detailed, size, object_type, custom_tags):
        key = "{}{}".format(base_url, object_type)
        if key in self.already_alerted:
            # We have already posted an event
            return

        self.already_alerted.append(key)

        title = (
            "RabbitMQ integration is approaching the limit on the number of {} that can be collected from on {}"
        ).format(object_type, self.hostname)
        msg = (
            "{} {} are present. The limit is {}. Please get in touch with Datadog support to increase the limit."
        ).format(size, object_type, max_detailed)

        event = {
            "timestamp": int(time.time()),
            "event_type": EVENT_TYPE,
            "msg_title": title,
            "msg_text": msg,
            "alert_type": 'warning',
            "source_type_name": SOURCE_TYPE_NAME,
            "host": self.hostname,
            "tags": ["base_url:{}".format(base_url), "host:{}".format(self.hostname)] + custom_tags,
            "event_object": "rabbitmq.limit.{}".format(object_type),
        }

        self.event(event)

    def _limit_vhosts(self, instance):
        """
        Check to see if vhosts were specified in the instance
        it will return a boolean, True if they were.
        This allows the check to only query the wanted vhosts.
        """
        vhosts = instance.get('vhosts', [])
        return len(vhosts) > 0

    def _check_aliveness(self, base_url, vhosts, custom_tags):
        """
        Check the aliveness API against all or a subset of vhosts. The API
        will return {"status": "ok"} and a 200 response code in the case
        that the check passes.
        """

        for vhost in vhosts:
            tags = ['vhost:{}'.format(vhost)] + custom_tags
            # We need to urlencode the vhost because it can be '/'.
            path = u'aliveness-test/{}'.format(quote_plus(vhost))
            aliveness_url = urljoin(base_url, path)
            aliveness_response = {}
            try:
                aliveness_response = self._get_data(aliveness_url)
            except Exception as e:
                self.log.debug("Couldn't get aliveness status from vhost, %s: %s", vhost, e)

            if aliveness_response.get('status') == 'ok':
                status = AgentCheck.OK
                message = None
            else:
                status = AgentCheck.CRITICAL
                message = u"Response from aliveness API: {}".format(aliveness_response)

            self.service_check('rabbitmq.aliveness', status, tags, message=message)
