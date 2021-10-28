# (C) Datadog, Inc. 2012-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from __future__ import division

import copy
import re
import socket
import time
from collections import defaultdict, namedtuple

from six import PY2, iteritems
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, is_affirmative, to_string
from datadog_checks.base.errors import CheckException

from .const import BUFSIZE, EVENT_TYPE, METRICS, SOURCE_TYPE_NAME, STATS_URL, UPTIME_PARSER, Services
from .version_utils import get_version_from_http, get_version_from_socket


class StickTable(namedtuple("StickTable", ["name", "type", "size", "used"])):

    SHOWTABLE_RE = re.compile(
        r"# table: (?P<name>[^ ,]+), type: (?P<type>[^ ,]+), size:(?P<size>[0-9]+), used:(?P<used>[0-9]+)$"
    )

    @classmethod
    def parse(cls, line):
        items = cls.SHOWTABLE_RE.match(line)
        if not items:
            return None
        return StickTable(
            name=items.group('name'),
            type=items.group('type'),
            size=int(items.group('size')),
            used=int(items.group('used')),
        )


class HAProxyCheckLegacy(AgentCheck):

    SERVICE_CHECK_NAME = 'haproxy.backend_up'
    HTTP_CONFIG_REMAPPER = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': False}}

    def __init__(self, name, init_config, instances):
        super(HAProxyCheckLegacy, self).__init__(name, init_config, instances)

        # Host status needs to persist across all checks.
        # We'll create keys when they are referenced. See:
        # https://en.wikipedia.org/wiki/Autovivification
        # https://gist.github.com/hrldcpr/2012250
        self.host_status = defaultdict(str)
        self.tags_regex = self.instance.get('tags_regex')
        self.custom_tags = tuple(self.instance.get('tags', []))
        self.url = self.instance.get('url')
        self.collect_aggregates_only = self.instance.get('collect_aggregates_only', True)
        self.collect_status_metrics = is_affirmative(self.instance.get('collect_status_metrics', False))
        self.collect_status_metrics_by_host = is_affirmative(self.instance.get('collect_status_metrics_by_host', False))
        self.collate_status_tags_per_host = is_affirmative(self.instance.get('collate_status_tags_per_host', False))
        self.count_status_by_service = is_affirmative(self.instance.get('count_status_by_service', True))
        self.tag_service_check_by_host = is_affirmative(self.instance.get('tag_service_check_by_host', False))
        self.enable_service_check = is_affirmative(self.instance.get('enable_service_check', False))
        self.startup_grace_period = float(self.instance.get('startup_grace_seconds', 0))
        self.services_incl_filter = self.instance.get('services_include', [])
        self.services_excl_filter = self.instance.get('services_exclude', [])
        self.include_active_tag = self.instance.get('active_tag', False)
        self.process_events = self.instance.get('status_check', self.init_config.get('status_check', False))

    def check(self, _):
        self.log.debug('Processing HAProxy data for %s', self.url)
        parsed_url = urlparse(self.url)
        tables = None

        if parsed_url.scheme == 'unix' or parsed_url.scheme == 'tcp':
            info, data, tables = self._fetch_socket_data(parsed_url)
            self._set_metadata(get_version_from_socket, info)
            uptime = self._collect_uptime_from_socket(info)
        else:
            try:
                uptime = self._collect_info_from_http()
            except Exception as e:
                self.log.warning("Couldn't collect version or uptime information: %s", e)
                uptime = None
            data = self._fetch_url_data()

        if uptime is not None and uptime < self.startup_grace_period:
            return

        if tables:
            self._process_stick_table_metrics(tables)

        self._process_data(data)

    @AgentCheck.metadata_entrypoint
    def _set_metadata(self, collection_method, version_info):
        version = collection_method(version_info)
        if version:
            self.log.debug("HAProxy version is %s", version)
            self.set_metadata('version', version)
        else:
            self.log.debug("unable to find HAProxy version info")

    def _fetch_url_data(self):
        """Hit a given http url and return the stats lines."""
        # Try to fetch data from the stats URL
        url = "%s%s" % (self.url, STATS_URL)

        self.log.debug("Fetching haproxy stats from url: %s", url)

        response = self.http.get(url)
        response.raise_for_status()
        return self._decode_response(response)

    @staticmethod
    def _decode_response(response):
        # it only needs additional decoding in py3, so skip it if it's py2
        if PY2:
            return response.content.splitlines()
        else:
            content = response.content

            # If the content is a string, it can't be decoded again
            # But if it's bytes, it can be decoded.
            # So, check if it has the decode method
            decode_fn = getattr(content, "decode", None)
            if callable(decode_fn):
                content = content.decode('utf-8')

            return content.splitlines()

    @staticmethod
    def _parse_uptime(uptime):
        matched_uptime = re.search(UPTIME_PARSER, uptime)
        return (
            int(matched_uptime.group('days')) * 86400
            + int(matched_uptime.group('hours')) * 3600
            + int(matched_uptime.group('minutes')) * 60
            + int(matched_uptime.group('seconds'))
        )

    def _collect_info_from_http(self):
        # the csv format does not offer version info, therefore we need to get the HTML page
        self.log.debug("collecting version info for HAProxy from %s", self.url)

        r = self.http.get(self.url)
        r.raise_for_status()
        raw_version = ""
        raw_uptime = ""
        uptime = None
        for line in self._decode_response(r):
            if "HAProxy version" in line:
                raw_version = line
            if "hapee-lb version" in line:
                # HAProxy enterprise edition
                raw_version = line
            if "uptime = " in line:
                raw_uptime = line
            if raw_uptime and raw_version:
                break

        self._set_metadata(get_version_from_http, raw_version)
        if raw_uptime == "":
            self.log.debug("unable to find HAProxy uptime")
        else:
            # It is not documented whether this output format is under any
            # compatibility guarantee, but it hasn't yet changed since it was
            # introduced
            uptime = self._parse_uptime(raw_uptime)

        return uptime

    @staticmethod
    def _run_socket_commands(parsed_url, commands):
        if parsed_url.scheme == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            splitted_loc = parsed_url.netloc.split(':')
            host = splitted_loc[0]
            port = int(splitted_loc[1])
            sock.connect((host, port))
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(parsed_url.path)

        sock.send(b';'.join(commands) + b"\r\n")

        response = ""
        output = sock.recv(BUFSIZE)
        while output:
            response += output.decode("ASCII")
            output = sock.recv(BUFSIZE)
        sock.close()

        responses = [r.strip() for r in response.split('\n\n') if r.strip()]

        if len(responses) != len(commands):
            raise CheckException("Expected {} responses, got {}".format(len(commands), len(responses)))

        return tuple(r.splitlines() for r in responses)

    def _fetch_socket_data(self, parsed_url):
        """Hit a given stats socket and return the stats lines."""

        self.log.debug("Fetching haproxy stats from socket: %s", parsed_url.geturl())
        info, stat = self._run_socket_commands(parsed_url, (b"show info", b"show stat"))

        # the "show table" command was introduced in 1.5. Sending "show table"
        # to a haproxy <1.5 results in no output at all even when multiple
        # commands were sent, so we have to check the version and only send the
        # command when supported
        tables = []
        raw_version = ''
        try:
            raw_version = get_version_from_socket(info)
            haproxy_major_version = tuple(int(vernum) for vernum in raw_version.split('.')[:2])

            if len(haproxy_major_version) == 2 and haproxy_major_version >= (1, 5):
                (tables,) = self._run_socket_commands(parsed_url, (b"show table",))
        except (IndexError, ValueError) as e:
            self.log.error("Could not parse version number '%s': %s", raw_version, e)
        except CheckException:
            # We got an empty response, which made _run_socket_commands raise an error
            self.log.debug("No tables returned")

        return info, stat, tables

    def _collect_uptime_from_socket(self, info):
        for line in info:
            key, value = line.split(':')
            if key == 'Uptime_sec':
                return int(value)

    def _process_data(self, data):
        """Main data-processing loop. For each piece of useful data, we'll
        either save a metric, save an event or both."""

        active_tag = []
        if self.include_active_tag:
            active_tag.append("active:%s" % ('true' if 'act' in data else 'false'))

        # Split the first line into an index of fields
        # The line looks like (broken up onto multiple lines)
        # "# pxname,svname,qcur,qmax,scur,smax,slim,
        # stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,
        # wredis,status,weight,act,bck,chkfail,chkdown,lastchg,
        # downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,
        # type,rate,rate_lim,rate_max,"
        fields = []
        for f in data[0].split(','):
            if f:
                f = f.replace('# ', '')
                fields.append(f.strip())

        self.hosts_statuses = defaultdict(int)

        back_or_front = None

        # Sanitize CSV, handle line breaks
        data = self._sanitize_lines(data)

        # Skip the first line, go backwards to set back_or_front
        for line in data[:0:-1]:
            if not line.strip():
                continue

            # Store each line's values in a dictionary
            data_dict = self._line_to_dict(fields, line)

            if self._is_aggregate(data_dict):
                back_or_front = data_dict['svname']

            self._update_data_dict(data_dict, back_or_front)

            self._update_hosts_statuses_if_needed(data_dict)

            # Clone the list to avoid extending the original
            # which would carry over previous iteration tags
            line_tags = list(self.custom_tags)

            regex_tags = self._tag_from_regex(data_dict['pxname'])
            if regex_tags:
                line_tags.extend(regex_tags)

            if self._should_process(data_dict):
                # update status
                # Send the list of data to the metric and event callbacks
                self._process_metrics(
                    data_dict,
                    custom_tags=line_tags,
                    active_tag=active_tag,
                )
            if self.process_events:
                self._process_event(
                    data_dict,
                    custom_tags=line_tags,
                )
            if self.enable_service_check:
                self._process_service_check(
                    data_dict,
                    custom_tags=line_tags,
                )

        if self.collect_status_metrics:
            self._process_status_metric(
                active_tag=active_tag,
            )

            self._process_backend_hosts_metric(
                active_tag=active_tag,
            )

        return data

    @staticmethod
    def _sanitize_lines(data):
        sanitized = []

        def char_count(line, char):
            count = 0

            for c in line:
                if c is char:
                    count += 1

            return count

        clean = ''
        double_quotes = 0
        for line in data:
            double_quotes += char_count(line, '"')
            clean += line

            if double_quotes % 2 == 0:
                sanitized.append(clean.replace('\n', '').replace('\r', ''))
                double_quotes = 0
                clean = ''

        return sanitized

    def _line_to_dict(self, fields, line):
        data_dict = {}
        values = line.split(',')
        if len(values) > len(fields):
            values = self._gather_quoted_values(values)
        for i, val in enumerate(values):
            if val:
                try:
                    # Try converting to a long, if failure, just leave it
                    val = float(val)
                except Exception:
                    pass
                data_dict[fields[i]] = val

        if 'status' in data_dict:
            data_dict['status'] = self._normalize_status(data_dict['status'])

        return data_dict

    @staticmethod
    def _gather_quoted_values(values):
        gathered_values = []
        previous = ''
        for val in values:
            if val.startswith('"') and not val.endswith('"'):
                previous = val
            elif previous:
                if val.endswith('"'):
                    gathered_values.append(previous + val)
                    previous = ''
                else:
                    previous += val
            else:
                gathered_values.append(val)
        return gathered_values

    @staticmethod
    def _update_data_dict(data_dict, back_or_front):
        """
        Adds spct if relevant, adds service
        """
        data_dict['back_or_front'] = back_or_front
        # The percentage of used sessions based on 'scur' and 'slim'
        if 'slim' in data_dict and 'scur' in data_dict:
            try:
                data_dict['spct'] = (data_dict['scur'] / data_dict['slim']) * 100
            except (TypeError, ZeroDivisionError):
                pass

    @staticmethod
    def _is_aggregate(data_dict):
        return data_dict['svname'] in Services.ALL

    def _update_hosts_statuses_if_needed(self, data_dict):
        if data_dict['svname'] == Services.BACKEND:
            return
        if self.collect_status_metrics and 'status' in data_dict and 'pxname' in data_dict:
            if self.collect_status_metrics_by_host and 'svname' in data_dict:
                key = (data_dict['pxname'], data_dict['back_or_front'], data_dict['svname'], data_dict['status'])
            else:
                key = (data_dict['pxname'], data_dict['back_or_front'], data_dict['status'])
            self.hosts_statuses[key] += 1

    def _should_process(self, data_dict):
        """if collect_aggregates_only, we process only the aggregates"""
        if is_affirmative(self.collect_aggregates_only):
            return self._is_aggregate(data_dict)
        elif str(self.collect_aggregates_only).lower() == 'both':
            return True

        return data_dict['svname'] != Services.BACKEND

    def _is_service_excl_filtered(self, service_name):
        if self._tag_match_patterns(service_name, self.services_excl_filter):
            if self._tag_match_patterns(service_name, self.services_incl_filter):
                return False
            return True
        return False

    @staticmethod
    def _tag_match_patterns(tag, filters):
        if not filters:
            return False
        for rule in filters:
            if re.search(rule, tag):
                return True
        return False

    def _tag_from_regex(self, service_name):
        """
        Use a named regexp on the current service_name to create extra tags
        Example HAProxy service name: be_edge_http_sre-prod_elk
        Example named regexp: be_edge_http_(?P<team>[a-z]+)\\-(?P<env>[a-z]+)_(?P<app>.*)
        Resulting tags: ['team:sre','env:prod','app:elk']
        """
        if not self.tags_regex or not service_name:
            return []

        match = re.compile(self.tags_regex).match(service_name)

        if not match:
            return []

        # match.groupdict() returns tags dictionary in the form of {'name': 'value'}
        # convert it to Datadog tag LIST: ['name:value']
        return ["%s:%s" % (name, value) for name, value in iteritems(match.groupdict())]

    @staticmethod
    def _normalize_status(status):
        """
        Try to normalize the HAProxy status as one of the statuses defined in `ALL_STATUSES`,
        if it can't be matched return the status as-is in a tag-friendly format
        ex: 'UP 1/2' -> 'up'
            'no check' -> 'no_check'
        """
        formatted_status = status.lower().replace(" ", "_")
        for normalized_status in Services.ALL_STATUSES:
            if formatted_status.startswith(normalized_status):
                return normalized_status
        return formatted_status

    def _process_backend_hosts_metric(self, active_tag=None):
        agg_statuses = defaultdict(lambda: {status: 0 for status in Services.COLLATED_STATUSES})
        active_tag = [] if active_tag is None else active_tag

        for host_status, count in iteritems(self.hosts_statuses):
            try:
                service, back_or_front, hostname, status = host_status
            except ValueError:
                service, back_or_front, status = host_status
            if back_or_front == 'FRONTEND':
                continue

            if self._is_service_excl_filtered(service):
                continue

            collated_status = Services.BACKEND_STATUS_TO_COLLATED.get(status)
            if collated_status:
                agg_statuses[service][collated_status] += count
            else:
                # create the entries for this service anyway
                agg_statuses[service]

        for service in agg_statuses:
            tags = self._tag_from_regex(service)
            tags.append('haproxy_service:%s' % service)
            tags.extend(self.custom_tags)
            tags.extend(active_tag)
            self._handle_legacy_service_tag(tags, service)

            self.gauge(
                'haproxy.backend_hosts', agg_statuses[service][Services.AVAILABLE], tags=tags + ['available:true']
            )
            self.gauge(
                'haproxy.backend_hosts', agg_statuses[service][Services.UNAVAILABLE], tags=tags + ['available:false']
            )
        return agg_statuses

    def _process_status_metric(
        self,
        active_tag=None,
    ):
        agg_statuses_counter = defaultdict(lambda: {status: 0 for status in Services.COLLATED_STATUSES})
        active_tag = [] if active_tag is None else active_tag
        # Initialize `statuses_counter`: every value is a defaultdict initialized with the correct
        # keys, which depends on the `collate_status_tags_per_host` option
        reported_statuses = Services.ALL_STATUSES
        if self.collate_status_tags_per_host:
            reported_statuses = Services.COLLATED_STATUSES
        reported_statuses_dict = defaultdict(int)
        for reported_status in reported_statuses:
            reported_statuses_dict[reported_status] = 0
        statuses_counter = defaultdict(lambda: copy.copy(reported_statuses_dict))

        for host_status, count in iteritems(self.hosts_statuses):
            hostname = None
            try:
                service, _, hostname, status = host_status
            except Exception:
                service, _, status = host_status
                if self.collect_status_metrics_by_host:
                    self.warning(
                        '`collect_status_metrics_by_host` is enabled but no host info could be extracted from HAProxy '
                        'stats endpoint for %s',
                        service,
                    )

            if self._is_service_excl_filtered(service):
                continue

            tags = self._tag_from_regex(service)
            if self.count_status_by_service:
                tags.append('haproxy_service:%s' % service)
                self._handle_legacy_service_tag(tags, service)
            if hostname:
                tags.append('backend:%s' % hostname)

            tags.extend(self.custom_tags)
            tags.extend(active_tag)

            counter_status = status
            if self.collate_status_tags_per_host:
                # An unknown status will be sent as UNAVAILABLE
                counter_status = Services.STATUS_TO_COLLATED.get(status, Services.UNAVAILABLE)
            statuses_counter[tuple(tags)][counter_status] += count

            # Compute aggregates with collated statuses. If collate_status_tags_per_host is enabled we
            # already send collated statuses with fine-grained tags, so no need to compute/send these aggregates
            if not self.collate_status_tags_per_host:
                agg_tags = []
                if self.count_status_by_service:
                    agg_tags.append('haproxy_service:%s' % service)
                    self._handle_legacy_service_tag(agg_tags, service)
                # An unknown status will be sent as UNAVAILABLE
                status_key = Services.STATUS_TO_COLLATED.get(status, Services.UNAVAILABLE)
                agg_statuses_counter[tuple(agg_tags)][status_key] += count

        for tags, count_per_status in iteritems(statuses_counter):
            for status, count in iteritems(count_per_status):
                self.gauge('haproxy.count_per_status', count, tags=tags + ('status:%s' % status,))

        # Send aggregates
        for service_tags, service_agg_statuses in iteritems(agg_statuses_counter):
            for status, count in iteritems(service_agg_statuses):
                self.gauge("haproxy.count_per_status", count, tags=service_tags + ('status:%s' % status,))

    def _process_metrics(self, data, custom_tags=None, active_tag=None):
        """
        Data is a dictionary related to one host
        (one line) extracted from the csv.
        It should look like:
        {'pxname':'dogweb', 'svname':'i-4562165', 'scur':'42', ...}
        """
        hostname = data['svname']
        service_name = data['pxname']
        back_or_front = data['back_or_front']
        custom_tags = [] if custom_tags is None else custom_tags
        active_tag = [] if active_tag is None else active_tag
        tags = ["type:%s" % back_or_front, "instance_url:%s" % self.url, "haproxy_service:%s" % service_name]
        tags.extend(custom_tags)
        tags.extend(active_tag)
        self._handle_legacy_service_tag(tags, service_name)

        if self._is_service_excl_filtered(service_name):
            return

        if back_or_front == Services.BACKEND:
            tags.append('backend:%s' % hostname)
            if data.get('addr'):
                tags.append('server_address:{}'.format(data.get('addr')))

        for key, value in data.items():
            if METRICS.get(key):
                if isinstance(METRICS[key], list):
                    for metric_tuple in METRICS[key]:
                        self._submit_metric_tuple(metric_tuple[0], metric_tuple[1], back_or_front, value, tags)
                else:
                    self._submit_metric_tuple(METRICS[key][0], METRICS[key][1], back_or_front, value, tags)

    def _submit_metric_tuple(self, metric_type, suffix, back_or_front, value, tags):
        name = "haproxy.%s.%s" % (back_or_front.lower(), suffix)
        try:
            if metric_type == 'rate':
                self.rate(name, float(value), tags=tags)
            else:
                self.gauge(name, float(value), tags=tags)
        except ValueError:
            pass

    def _process_stick_table_metrics(self, data, services_incl_filter=None, services_excl_filter=None):
        """
        Stick table metrics processing. Two metrics will be created for each stick table (current and max size)
        """
        for line in data:
            table = StickTable.parse(line)
            if table is None:
                continue
            if self._is_service_excl_filtered(table.name):
                continue

            tags = ["haproxy_service:%s" % table.name, "stick_type:%s" % table.type]
            tags.extend(self.custom_tags)
            self.gauge("haproxy.sticktable.size", float(table.size), tags=tags)
            self.gauge("haproxy.sticktable.used", float(table.used), tags=tags)

    def _process_event(self, data, custom_tags=None):
        """
        Main event processing loop. An event will be created for a service
        status change.
        Service checks on the server side can be used to provide the same functionality
        """
        hostname = data['svname']
        service_name = data['pxname']
        key = "%s:%s" % (hostname, service_name)
        status = self.host_status[key]
        custom_tags = [] if custom_tags is None else custom_tags

        if self._is_service_excl_filtered(service_name):
            return

        data_status = data['status']
        if status is None:
            self.host_status[key] = data_status
            return

        if status != data_status and data_status in ('up', 'down'):
            # If the status of a host has changed, we trigger an event
            try:
                lastchg = int(data['lastchg'])
            except Exception:
                lastchg = 0

            # Create the event object
            ev = self._create_event(
                data_status, hostname, lastchg, service_name, data['back_or_front'], custom_tags=custom_tags
            )
            self.event(ev)

            # Store this host status so we can check against it later
            self.host_status[key] = data_status

    def _create_event(self, status, hostname, lastchg, service_name, back_or_front, custom_tags=None):
        custom_tags = [] if custom_tags is None else custom_tags
        if status == 'down':
            alert_type = "error"
            title = "%s reported %s:%s %s" % (self.hostname, service_name, hostname, status.upper())
        else:
            if status == "up":
                alert_type = "success"
            else:
                alert_type = "info"
            title = "%s reported %s:%s back and %s" % (self.hostname, service_name, hostname, status.upper())

        tags = ["haproxy_service:%s" % service_name]
        if back_or_front == Services.BACKEND:
            tags.append('backend:%s' % hostname)
        tags.extend(custom_tags)
        self._handle_legacy_service_tag(tags, service_name)

        return {
            'timestamp': int(time.time() - lastchg),
            'event_type': EVENT_TYPE,
            'host': self.hostname,
            'msg_title': title,
            'alert_type': alert_type,
            "source_type_name": SOURCE_TYPE_NAME,
            "event_object": hostname,
            "tags": tags,
        }

    def _process_service_check(self, data, custom_tags=None):
        """Report a service check, tagged by the service and the backend.
        Statuses are defined in `STATUS_TO_SERVICE_CHECK` mapping.
        """
        custom_tags = [] if custom_tags is None else custom_tags
        service_name = data['pxname']
        status = data['status']
        haproxy_hostname = to_string(self.hostname)
        check_hostname = haproxy_hostname if self.tag_service_check_by_host else ''

        if self._is_service_excl_filtered(service_name):
            return

        if status in Services.STATUS_TO_SERVICE_CHECK:
            service_check_tags = ["haproxy_service:%s" % service_name]
            service_check_tags.extend(custom_tags)
            self._handle_legacy_service_tag(service_check_tags, service_name)

            hostname = data['svname']
            if data['back_or_front'] == Services.BACKEND:
                service_check_tags.append('backend:%s' % hostname)

            status = Services.STATUS_TO_SERVICE_CHECK[status]
            message = (
                "%s reported %s:%s %s" % (haproxy_hostname, service_name, hostname, status)
                if status is not AgentCheck.OK
                else None
            )
            self.service_check(
                self.SERVICE_CHECK_NAME, status, message=message, hostname=check_hostname, tags=service_check_tags
            )

    def _handle_legacy_service_tag(self, tags, service):
        if not self.instance.get('disable_legacy_service_tag', False):
            self._log_deprecation('service_tag', 'haproxy_service')
            tags.append('service:{}'.format(service))
