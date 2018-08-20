# (C) Datadog, Inc. 2013-2017
# (C) Brett Langdon <brett@blangdon.com> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import re
import time
import urllib
import urlparse
from collections import defaultdict

# 3p
import requests
from requests.exceptions import RequestException

# project
from datadog_checks.checks import AgentCheck
from datadog_checks.config import _is_affirmative

EVENT_TYPE = SOURCE_TYPE_NAME = 'rabbitmq'
EXCHANGE_TYPE = 'exchanges'
QUEUE_TYPE = 'queues'
NODE_TYPE = 'nodes'
CONNECTION_TYPE = 'connections'
MAX_DETAILED_EXCHANGES = 50
MAX_DETAILED_QUEUES = 200
MAX_DETAILED_NODES = 100
# Post an event in the stream when the number of queues or nodes to
# collect is above 90% of the limit:
ALERT_THRESHOLD = 0.9
EXCHANGE_ATTRIBUTES = [
    # Path, Name, Operation
    ('message_stats/ack', 'messages.ack.count', float),
    ('message_stats/ack_details/rate', 'messages.ack.rate', float),

    ('message_stats/confirm', 'messages.confirm.count', float),
    ('message_stats/confirm_details/rate', 'messages.confirm.rate', float),

    ('message_stats/deliver_get', 'messages.deliver_get.count', float),
    ('message_stats/deliver_get_details/rate', 'messages.deliver_get.rate', float),

    ('message_stats/publish', 'messages.publish.count', float),
    ('message_stats/publish_details/rate', 'messages.publish.rate', float),

    ('message_stats/publish_in', 'messages.publish_in.count', float),
    ('message_stats/publish_in_details/rate', 'messages.publish_in.rate', float),

    ('message_stats/publish_out', 'messages.publish_out.count', float),
    ('message_stats/publish_out_details/rate', 'messages.publish_out.rate', float),

    ('message_stats/return_unroutable', 'messages.return_unroutable.count', float),
    ('message_stats/return_unroutable_details/rate', 'messages.return_unroutable.rate', float),

    ('message_stats/redeliver', 'messages.redeliver.count', float),
    ('message_stats/redeliver_details/rate', 'messages.redeliver.rate', float),
]
QUEUE_ATTRIBUTES = [
    # Path, Name, Operation
    ('active_consumers', 'active_consumers', float),
    ('consumers', 'consumers', float),
    ('consumer_utilisation', 'consumer_utilisation', float),

    ('memory', 'memory', float),

    ('messages', 'messages', float),
    ('messages_details/rate', 'messages.rate', float),

    ('messages_ready', 'messages_ready', float),
    ('messages_ready_details/rate', 'messages_ready.rate', float),

    ('messages_unacknowledged', 'messages_unacknowledged', float),
    ('messages_unacknowledged_details/rate', 'messages_unacknowledged.rate', float),

    ('message_stats/ack', 'messages.ack.count', float),
    ('message_stats/ack_details/rate', 'messages.ack.rate', float),

    ('message_stats/deliver', 'messages.deliver.count', float),
    ('message_stats/deliver_details/rate', 'messages.deliver.rate', float),

    ('message_stats/deliver_get', 'messages.deliver_get.count', float),
    ('message_stats/deliver_get_details/rate', 'messages.deliver_get.rate', float),

    ('message_stats/publish', 'messages.publish.count', float),
    ('message_stats/publish_details/rate', 'messages.publish.rate', float),

    ('message_stats/redeliver', 'messages.redeliver.count', float),
    ('message_stats/redeliver_details/rate', 'messages.redeliver.rate', float),
]

NODE_ATTRIBUTES = [
    ('fd_used', 'fd_used', float),
    ('disk_free', 'disk_free', float),
    ('mem_used', 'mem_used', float),
    ('run_queue', 'run_queue', float),
    ('sockets_used', 'sockets_used', float),
    ('partitions', 'partitions', len),
    ('running', 'running', float),
    ('mem_alarm', 'mem_alarm', float),
    ('disk_free_alarm', 'disk_alarm', float),
]

ATTRIBUTES = {
    EXCHANGE_TYPE: EXCHANGE_ATTRIBUTES,
    QUEUE_TYPE: QUEUE_ATTRIBUTES,
    NODE_TYPE: NODE_ATTRIBUTES,
}

TAG_PREFIX = 'rabbitmq'
TAGS_MAP = {
    EXCHANGE_TYPE: {
        'name': 'exchange',
        'vhost': 'vhost',
        'exchange_family': 'exchange_family',
    },
    QUEUE_TYPE: {
        'node': 'node',
        'name': 'queue',
        'vhost': 'vhost',
        'policy': 'policy',
        'queue_family': 'queue_family',
    },
    NODE_TYPE: {
        'name': 'node',
    }
}

METRIC_SUFFIX = {
    EXCHANGE_TYPE: "exchange",
    QUEUE_TYPE: "queue",
    NODE_TYPE: "node",
}


class RabbitMQException(Exception):
    pass


class RabbitMQ(AgentCheck):

    """This check is for gathering statistics from the RabbitMQ
    Management Plugin (http://www.rabbitmq.com/management.html)
    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.already_alerted = []
        self.cached_vhosts = {}  # this is used to send CRITICAL rabbitmq.aliveness check if the server goes down

    def _get_config(self, instance):
        # make sure 'rabbitmq_api_url' is present and get parameters
        base_url = instance.get('rabbitmq_api_url', None)
        if not base_url:
            raise Exception('Missing "rabbitmq_api_url" in RabbitMQ config.')
        if not base_url.endswith('/'):
            base_url += '/'
        username = instance.get('rabbitmq_user', 'guest')
        password = instance.get('rabbitmq_pass', 'guest')
        custom_tags = instance.get('tags', [])
        parsed_url = urlparse.urlparse(base_url)
        if not parsed_url.scheme or "://" not in parsed_url.geturl():
            self.log.warning('The rabbit url did not include a protocol, assuming http')
            # urlparse.urljoin cannot add a protocol to the rest of the url for some reason.
            # This still leaves the potential for errors, but such urls would never have been valid, either
            # and it's not likely to be useful to attempt to catch all possible mistakes people could make.
            # urlparse also has a known issue parsing url with no schema, but a port in the host section
            # mistakingly taking the host for the schema, hence the additional validation
            base_url = 'http://' + base_url
            parsed_url = urlparse.urlparse(base_url)

        ssl_verify = _is_affirmative(instance.get('ssl_verify', True))
        if not ssl_verify and parsed_url.scheme == 'https':
            self.log.warning('Skipping SSL cert validation for %s based on configuration.' % (base_url))

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
            QUEUE_TYPE: {
                'explicit': instance.get('queues', []),
                'regexes': instance.get('queues_regexes', []),
            },
            NODE_TYPE: {
                'explicit': instance.get('nodes', []),
                'regexes': instance.get('nodes_regexes', []),
            },
        }

        for object_type, filters in specified.iteritems():
            for filter_type, filter_objects in filters.iteritems():
                if type(filter_objects) != list:
                    raise TypeError(
                        "{0} / {0}_regexes parameter must be a list".format(object_type))

        auth = (username, password)

        return base_url, max_detailed, specified, auth, ssl_verify, custom_tags

    def _get_vhosts(self, instance, base_url, auth=None, ssl_verify=True):
        vhosts = instance.get('vhosts')

        if not vhosts:
            # Fetch a list of _all_ vhosts from the API.
            vhosts_url = urlparse.urljoin(base_url, 'vhosts')
            vhost_proxy = self.get_instance_proxy(instance, vhosts_url)
            vhosts_response = self._get_data(vhosts_url, auth=auth, ssl_verify=ssl_verify, proxies=vhost_proxy)
            vhosts = [v['name'] for v in vhosts_response]

        return vhosts

    def check(self, instance):
        base_url, max_detailed, specified, auth, ssl_verify, custom_tags = self._get_config(instance)
        try:
            vhosts = self._get_vhosts(instance, base_url, auth=auth, ssl_verify=ssl_verify)
            self.cached_vhosts[base_url] = vhosts

            limit_vhosts = []
            if self._limit_vhosts(instance):
                limit_vhosts = vhosts

            # Generate metrics from the status API.
            self.get_stats(instance, base_url, EXCHANGE_TYPE, max_detailed[EXCHANGE_TYPE], specified[EXCHANGE_TYPE],
                           limit_vhosts, custom_tags, auth=auth, ssl_verify=ssl_verify)
            self.get_stats(instance, base_url, QUEUE_TYPE, max_detailed[QUEUE_TYPE], specified[QUEUE_TYPE],
                           limit_vhosts, custom_tags, auth=auth, ssl_verify=ssl_verify)
            self.get_stats(instance, base_url, NODE_TYPE, max_detailed[NODE_TYPE], specified[NODE_TYPE],
                           limit_vhosts, custom_tags, auth=auth, ssl_verify=ssl_verify)

            self.get_connections_stat(instance, base_url, CONNECTION_TYPE, vhosts, limit_vhosts, custom_tags,
                                      auth=auth, ssl_verify=ssl_verify)

            # Generate a service check from the aliveness API. In the case of an invalid response
            # code or unparseable JSON this check will send no data.
            self._check_aliveness(instance, base_url, vhosts, custom_tags, auth=auth, ssl_verify=ssl_verify)

            # Generate a service check for the service status.
            self.service_check('rabbitmq.status', AgentCheck.OK, custom_tags)

        except RabbitMQException as e:
            msg = "Error executing check: {}".format(e)
            self.service_check('rabbitmq.status', AgentCheck.CRITICAL, custom_tags, message=msg)
            self.log.error(msg)

            # tag every vhost as CRITICAL or they would keep the latest value, OK, in case the RabbitMQ server goes down
            msg = "error while contacting rabbitmq (%s), setting aliveness to CRITICAL for vhosts: %s"
            msg = msg % (base_url, self.cached_vhosts)
            self.log.error(msg)
            for vhost in self.cached_vhosts.get(base_url, []):
                self.service_check('rabbitmq.aliveness',
                                   AgentCheck.CRITICAL,
                                   ['vhost:%s' % vhost] + custom_tags,
                                   message=u"Could not contact aliveness API")

    def _get_data(self, url, auth=None, ssl_verify=True, proxies=None):
        if proxies is None:
            proxies = {}
        try:
            r = requests.get(url,
                             auth=auth,
                             proxies=proxies,
                             timeout=self.default_integration_http_timeout,
                             verify=ssl_verify)
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

                match_found = False
                for p in regex_filters:
                    match = re.search(p, name)
                    if match:
                        if _is_affirmative(tag_families) and match.groups():
                            if object_type == QUEUE_TYPE:
                                data_line["queue_family"] = match.groups()[0]
                            if object_type == EXCHANGE_TYPE:
                                data_line["exchange_family"] = match.groups()[0]
                        matching_lines.append(data_line)
                        match_found = True
                        break

                if match_found:
                    continue

                # Absolute names work only for queues and exchanges
                if object_type != QUEUE_TYPE and object_type != EXCHANGE_TYPE:
                    continue
                absolute_name = '%s/%s' % (data_line.get("vhost"), name)
                if absolute_name in explicit_filters:
                    matching_lines.append(data_line)
                    explicit_filters.remove(absolute_name)
                    continue

                for p in regex_filters:
                    match = re.search(p, absolute_name)
                    if match:
                        if _is_affirmative(tag_families) and match.groups():
                            if object_type == QUEUE_TYPE:
                                data_line["queue_family"] = match.groups()[0]
                            if object_type == EXCHANGE_TYPE:
                                data_line["exchange_family"] = match.groups()[0]
                        matching_lines.append(data_line)
                        match_found = True
                        break
                if match_found:
                    continue
            return matching_lines
        return data

    def _get_tags(self, data, object_type, custom_tags):
        tags = []
        tag_list = TAGS_MAP[object_type]
        for t in tag_list:
            tag = data.get(t)
            if tag:
                # FIXME 6.x: remove this suffix or unify (sc doesn't have it)
                tags.append('%s_%s:%s' % (TAG_PREFIX, tag_list[t], tag))
        return tags + custom_tags

    def get_stats(self, instance, base_url, object_type, max_detailed,
                  filters, limit_vhosts, custom_tags, auth=None, ssl_verify=True):
        """
        instance: the check instance
        base_url: the url of the rabbitmq management api (e.g. http://localhost:15672/api)
        object_type: either QUEUE_TYPE or NODE_TYPE or EXCHANGE_TYPE
        max_detailed: the limit of objects to collect for this type
        filters: explicit or regexes filters of specified queues or nodes (specified in the yaml file)
        """
        instance_proxy = self.get_instance_proxy(instance, base_url)
        # Make a copy of this list as we will remove items from it at each
        # iteration
        explicit_filters = list(filters['explicit'])
        regex_filters = filters['regexes']

        data = []

        # only do this if vhosts were specified,
        # otherwise it'll just be making more queries for the same data
        if self._limit_vhosts(instance) and object_type == QUEUE_TYPE:
            for vhost in limit_vhosts:
                url = '{}/{}'.format(object_type, urllib.quote_plus(vhost))
                try:
                    data += self._get_data(urlparse.urljoin(base_url, url), auth=auth,
                                           ssl_verify=ssl_verify, proxies=instance_proxy)
                except Exception as e:
                    self.log.debug("Couldn't grab queue data from vhost, {}: {}".format(vhost, e))
        else:
            data = self._get_data(urlparse.urljoin(base_url, object_type), auth=auth,
                                  ssl_verify=ssl_verify, proxies=instance_proxy)

        """ data is a list of nodes or queues:
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
        if len(explicit_filters) > max_detailed:
            raise Exception(
                "The maximum number of %s you can specify is %d." % (object_type, max_detailed))

        # a list of queues/nodes is specified. We process only those
        data = self._filter_list(data,
                                 explicit_filters,
                                 regex_filters,
                                 object_type,
                                 instance.get("tag_families", False))

        # if no filters are specified, check everything according to the limits
        if len(data) > ALERT_THRESHOLD * max_detailed:
            # Post a message on the dogweb stream to warn
            self.alert(base_url, max_detailed, len(data), object_type, custom_tags)

        if len(data) > max_detailed:
            # Display a warning in the info page
            msg = ("Too many items to fetch. "
                   "You must choose the %s you are interested in by editing the rabbitmq.yaml configuration file"
                   "or get in touch with Datadog Support")
            msg = msg % object_type
            self.warning(msg)

        for data_line in data[:max_detailed]:
            # We truncate the list if it's above the limit
            self._get_metrics(data_line, object_type, custom_tags)

        # get a list of the number of bindings on a given queue
        # /api/queues/vhost/name/bindings
        if object_type is QUEUE_TYPE:
            self._get_queue_bindings_metrics(base_url, custom_tags, data, instance_proxy,
                                             instance, object_type, auth, ssl_verify)

    def _get_metrics(self, data, object_type, custom_tags):
        tags = self._get_tags(data, object_type, custom_tags)
        for attribute, metric_name, operation in ATTRIBUTES[object_type]:
            # Walk down through the data path, e.g. foo/bar => d['foo']['bar']
            root = data
            keys = attribute.split('/')
            for path in keys[:-1]:
                root = root.get(path, {})

            value = root.get(keys[-1], None)
            if value is not None:
                try:
                    self.gauge('rabbitmq.%s.%s' % (
                        METRIC_SUFFIX[object_type], metric_name), operation(value), tags=tags)
                except ValueError:
                    self.log.debug("Caught ValueError for %s %s = %s  with tags: %s" % (
                        METRIC_SUFFIX[object_type], attribute, value, tags))

    def _get_queue_bindings_metrics(self, base_url, custom_tags, data, instance_proxy,
                                    instance, object_type, auth=None, ssl_verify=True):
        for item in data:
            vhost = item['vhost']
            tags = self._get_tags(item, object_type, custom_tags)
            url = '{}/{}/{}/bindings'.format(QUEUE_TYPE, urllib.quote_plus(vhost), urllib.quote_plus(item['name']))
            bindings_count = len(self._get_data(urlparse.urljoin(base_url, url), auth=auth,
                                 ssl_verify=ssl_verify, proxies=instance_proxy))

            self.gauge('rabbitmq.queue.bindings.count', bindings_count, tags)

    def get_connections_stat(self, instance, base_url,
                             object_type, vhosts, limit_vhosts,
                             custom_tags, auth=None, ssl_verify=True):
        """
        Collect metrics on currently open connection per vhost.
        """
        instance_proxy = self.get_instance_proxy(instance, base_url)

        grab_all_data = True

        if self._limit_vhosts(instance):
            grab_all_data = False
            data = []
            for vhost in vhosts:
                url = "vhosts/{}/{}".format(urllib.quote_plus(vhost), object_type)
                try:
                    data += self._get_data(urlparse.urljoin(base_url, url), auth=auth,
                                           ssl_verify=ssl_verify, proxies=instance_proxy)
                except Exception as e:
                    # This will happen if there is no connection data to grab
                    self.log.debug("Couldn't grab connection data from vhost, {}: {}".format(vhost, e))

        # sometimes it seems to need to fall back to this
        if grab_all_data or not len(data):
            data = self._get_data(urlparse.urljoin(base_url, object_type), auth=auth,
                                  ssl_verify=ssl_verify, proxies=instance_proxy)

        stats = {vhost: 0 for vhost in vhosts}
        connection_states = defaultdict(int)
        for conn in data:
            if conn['vhost'] in vhosts:
                stats[conn['vhost']] += 1
                # 'state' does not exist for direct type connections.
                connection_states[conn.get('state', 'direct')] += 1

        for vhost, nb_conn in stats.iteritems():
            self.gauge('rabbitmq.connections', nb_conn, tags=['%s_vhost:%s' % (TAG_PREFIX, vhost)] + custom_tags)

        for conn_state, nb_conn in connection_states.iteritems():
            self.gauge('rabbitmq.connections.state',
                       nb_conn,
                       tags=['%s_conn_state:%s' % (TAG_PREFIX, conn_state)] + custom_tags)

    def alert(self, base_url, max_detailed, size, object_type, custom_tags):
        key = "%s%s" % (base_url, object_type)
        if key in self.already_alerted:
            # We have already posted an event
            return

        self.already_alerted.append(key)

        title = "RabbitMQ integration is approaching the limit on the number of %s that can be collected from on %s" % (
            object_type, self.hostname)
        msg = """%s %s are present. The limit is %s.
        Please get in touch with Datadog support to increase the limit.""" % (size, object_type, max_detailed)

        event = {
            "timestamp": int(time.time()),
            "event_type": EVENT_TYPE,
            "msg_title": title,
            "msg_text": msg,
            "alert_type": 'warning',
            "source_type_name": SOURCE_TYPE_NAME,
            "host": self.hostname,
            "tags": ["base_url:%s" % base_url, "host:%s" % self.hostname] + custom_tags,
            "event_object": "rabbitmq.limit.%s" % object_type,
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

    def _check_aliveness(self, instance, base_url, vhosts, custom_tags, auth=None, ssl_verify=True):
        """
        Check the aliveness API against all or a subset of vhosts. The API
        will return {"status": "ok"} and a 200 response code in the case
        that the check passes.
        """

        for vhost in vhosts:
            tags = ['vhost:%s' % vhost] + custom_tags
            # We need to urlencode the vhost because it can be '/'.
            path = u'aliveness-test/%s' % (urllib.quote_plus(vhost))
            aliveness_url = urlparse.urljoin(base_url, path)
            aliveness_proxy = self.get_instance_proxy(instance, aliveness_url)
            aliveness_response = self._get_data(aliveness_url,
                                                auth=auth,
                                                ssl_verify=ssl_verify,
                                                proxies=aliveness_proxy)
            message = u"Response from aliveness API: %s" % aliveness_response

            if aliveness_response.get('status') == 'ok':
                status = AgentCheck.OK
            else:
                status = AgentCheck.CRITICAL

            self.service_check('rabbitmq.aliveness', status, tags, message=message)
