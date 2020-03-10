# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import fnmatch
import functools
import ipaddress
import json
import threading
import time
from collections import defaultdict
from concurrent import futures
from typing import Any, DefaultDict, Dict, List, Optional, Tuple, Union

from pyasn1.codec.ber.decoder import decode as pyasn1_decode
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.errors import CheckException
from datadog_checks.base.types import ServiceCheckStatus

from .commands import snmp_bulk, snmp_get, snmp_getnext
from .compat import read_persistent_cache, total_time_to_temporal_percent, write_persistent_cache
from .config import InstanceConfig, ParsedMetric, ParsedMetricTag, ParsedTableMetric
from .exceptions import PySnmpError
from .models import (
    Counter32,
    Counter64,
    CounterBasedGauge64,
    Gauge32,
    Integer,
    Integer32,
    ObjectIdentity,
    ObjectType,
    Unsigned32,
    ZeroBasedCounter64,
    noSuchInstance,
    noSuchObject,
)
from .utils import OIDPrinter, get_profile_definition, oid_pattern_specificity, recursively_expand_base_profiles

# Metric type that we support
SNMP_COUNTERS = frozenset([Counter32.__name__, Counter64.__name__, ZeroBasedCounter64.__name__])

SNMP_GAUGES = frozenset(
    [Gauge32.__name__, Unsigned32.__name__, CounterBasedGauge64.__name__, Integer.__name__, Integer32.__name__]
)

DEFAULT_OID_BATCH_SIZE = 10


def reply_invalid(oid):
    # type: (Any) -> bool
    return noSuchInstance.isSameTypeWith(oid) or noSuchObject.isSameTypeWith(oid)


class SnmpCheck(AgentCheck):

    SC_STATUS = 'snmp.can_check'
    _running = True
    _thread = None
    _executor = None
    _NON_REPEATERS = 0
    _MAX_REPETITIONS = 25

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(SnmpCheck, self).__init__(*args, **kwargs)

        # Set OID batch size
        self.oid_batch_size = int(self.init_config.get('oid_batch_size', DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = self.init_config.get('mibs_folder')

        self.ignore_nonincreasing_oid = is_affirmative(self.init_config.get('ignore_nonincreasing_oid', False))

        self.profiles = self.init_config.get('profiles', {})  # type: Dict[str, Dict[str, Any]]
        self.profiles_by_oid = {}  # type: Dict[str, str]
        self._load_profiles()

        self.instance['name'] = self._get_instance_name(self.instance)
        self._config = self._build_config(self.instance)

    def _load_profiles(self):
        # type: () -> None
        """
        Load the configured SNMP profiles and index them by sysObjectID, if possible.
        """
        for name, profile in self.profiles.items():
            try:
                definition = get_profile_definition(profile)
            except Exception as exc:
                raise ConfigurationError("Couldn't read profile '{}': {}".format(name, exc))

            try:
                recursively_expand_base_profiles(definition)
            except Exception as exc:
                raise ConfigurationError("Failed to expand base profiles in profile '{}': {}".format(name, exc))

            self.profiles[name] = {'definition': definition}
            sys_object_oid = definition.get('sysobjectid')
            if sys_object_oid is not None:
                self.profiles_by_oid[sys_object_oid] = name

    def _build_config(self, instance):
        # type: (dict) -> InstanceConfig
        return InstanceConfig(
            instance,
            warning=self.warning,
            global_metrics=self.init_config.get('global_metrics', []),
            mibs_path=self.mibs_path,
            profiles=self.profiles,
            profiles_by_oid=self.profiles_by_oid,
        )

    def _get_instance_name(self, instance):
        # type: (Dict[str, Any]) -> Optional[str]
        name = instance.get('name')
        if name:
            return name

        ip = instance.get('ip_address')  # type: Optional[str]
        port = instance.get('port')  # type: Optional[int]

        if ip and port:
            return '{host}:{port}'.format(host=ip, port=port)
        elif ip:
            return ip
        else:
            return None

    def discover_instances(self, interval):
        # type: (float) -> None
        config = self._config

        while self._running:
            start_time = time.time()
            for host in config.network_hosts():
                instance = copy.deepcopy(config.instance)
                instance.pop('network_address')
                instance['ip_address'] = host

                host_config = self._build_config(instance)

                try:
                    sys_object_oid = self.fetch_sysobject_oid(host_config)
                except Exception as e:
                    self.log.debug("Error scanning host %s: %s", host, e)
                    continue

                try:
                    profile = self._profile_for_sysobject_oid(sys_object_oid)
                except ConfigurationError:
                    if not (host_config.all_oids or host_config.bulk_oids):
                        self.log.warning("Host %s didn't match a profile for sysObjectID %s", host, sys_object_oid)
                        continue
                else:
                    host_config.refresh_with_profile(self.profiles[profile], self.warning)
                    host_config.add_profile_tag(profile)

                config.discovered_instances[host] = host_config

                write_persistent_cache(self.check_id, json.dumps(list(config.discovered_instances)))

            # Write again at the end of the loop, in case some host have been removed since last
            write_persistent_cache(self.check_id, json.dumps(list(config.discovered_instances)))

            time_elapsed = time.time() - start_time
            if interval - time_elapsed > 0:
                time.sleep(interval - time_elapsed)

    def fetch_results(self, config, all_oids, bulk_oids):
        # type: (InstanceConfig, list, list) -> Tuple[dict, Optional[str]]
        """
        Perform a snmpwalk on the domain specified by the oids, on the device
        configured in instance.

        Returns a dictionary:
        dict[oid/metric_name][row index] = value
        In case of scalar objects, the row index is just 0
        """
        results = defaultdict(dict)  # type: DefaultDict[str, dict]
        enforce_constraints = config.enforce_constraints

        all_binds, error = self.fetch_oids(config, all_oids, enforce_constraints=enforce_constraints)

        for oid in bulk_oids:
            try:
                self.log.debug('Running SNMP command getBulk on OID %r', oid)
                binds = snmp_bulk(
                    config,
                    oid,
                    self._NON_REPEATERS,
                    self._MAX_REPETITIONS,
                    enforce_constraints,
                    self.ignore_nonincreasing_oid,
                )
                all_binds.extend(binds)
            except PySnmpError as e:
                message = 'Failed to collect some metrics: {}'.format(e)
                if not error:
                    error = message
                self.warning(message)

        for result_oid, value in all_binds:
            metric, indexes = config.resolve_oid(result_oid)
            results[metric][indexes] = value
        self.log.debug('Raw results: %s', OIDPrinter(results, with_values=False))
        # Freeze the result
        results.default_factory = None
        return results, error

    def fetch_oids(self, config, oids, enforce_constraints):
        # type: (InstanceConfig, list, bool) -> Tuple[List[Any], Optional[str]]
        # UPDATE: We used to perform only a snmpgetnext command to fetch metric values.
        # It returns the wrong value when the OID passed is referring to a specific leaf.
        # For example:
        # snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.4.2.1.7.222
        # iso.3.6.1.2.1.25.4.2.1.7.224 = INTEGER: 2
        # SOLUTION: perform a snmpget command and fallback with snmpgetnext if not found
        error = None
        first_oid = 0
        all_binds = []
        while first_oid < len(oids):
            try:
                oids_batch = oids[first_oid : first_oid + self.oid_batch_size]
                self.log.debug('Running SNMP command get on OIDS: %s', OIDPrinter(oids_batch, with_values=False))

                var_binds = snmp_get(config, oids_batch, lookup_mib=enforce_constraints)
                self.log.debug('Returned vars: %s', OIDPrinter(var_binds, with_values=True))

                missing_results = []

                for var in var_binds:
                    result_oid, value = var
                    if reply_invalid(value):
                        oid_tuple = result_oid.asTuple()
                        missing_results.append(ObjectType(ObjectIdentity(oid_tuple)))
                    else:
                        all_binds.append(var)

                if missing_results:
                    # If we didn't catch the metric using snmpget, try snmpnext
                    # Don't walk through the entire MIB, stop at end of table
                    self.log.debug(
                        'Running SNMP command getNext on OIDS: %s', OIDPrinter(missing_results, with_values=False)
                    )
                    binds = list(
                        snmp_getnext(
                            config,
                            missing_results,
                            lookup_mib=enforce_constraints,
                            ignore_nonincreasing_oid=self.ignore_nonincreasing_oid,
                        )
                    )
                    self.log.debug('Returned vars: %s', OIDPrinter(binds, with_values=True))
                    all_binds.extend(binds)

            except PySnmpError as e:
                message = 'Failed to collect some metrics: {}'.format(e)
                if not error:
                    error = message
                self.warning(message)

            # if we fail move onto next batch
            first_oid += self.oid_batch_size

        return all_binds, error

    def fetch_sysobject_oid(self, config):
        # type: (InstanceConfig) -> str
        """Return the sysObjectID of the instance."""
        # Reference sysObjectID directly, see http://oidref.com/1.3.6.1.2.1.1.2
        oid = ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 1, 2, 0)))
        self.log.debug('Running SNMP command on OID: %r', OIDPrinter((oid,), with_values=False))
        var_binds = snmp_get(config, [oid], lookup_mib=False)
        self.log.debug('Returned vars: %s', OIDPrinter(var_binds, with_values=True))
        return var_binds[0][1].prettyPrint()

    def _profile_for_sysobject_oid(self, sys_object_oid):
        # type: (str) -> str
        """
        Return the most specific profile that matches the given sysObjectID.
        """
        profiles = [profile for oid, profile in self.profiles_by_oid.items() if fnmatch.fnmatch(sys_object_oid, oid)]

        if not profiles:
            raise ConfigurationError('No profile matching sysObjectID {}'.format(sys_object_oid))

        return max(
            profiles, key=lambda profile: oid_pattern_specificity(self.profiles[profile]['definition']['sysobjectid'])
        )

    def _start_discovery(self):
        # type: () -> None
        cache = read_persistent_cache(self.check_id)
        if cache:
            hosts = json.loads(cache)
            for host in hosts:
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    write_persistent_cache(self.check_id, json.dumps([]))
                    break
                instance = copy.deepcopy(self.instance)
                instance.pop('network_address')
                instance['ip_address'] = host

                host_config = self._build_config(instance)
                self._config.discovered_instances[host] = host_config

        raw_discovery_interval = self._config.instance.get('discovery_interval', 3600)
        try:
            discovery_interval = float(raw_discovery_interval)
        except (ValueError, TypeError):
            message = 'discovery_interval could not be parsed as a number: {!r}'.format(raw_discovery_interval)
            raise ConfigurationError(message)

        self._thread = threading.Thread(target=self.discover_instances, args=(discovery_interval,), name=self.name)
        self._thread.daemon = True
        self._thread.start()
        self._executor = futures.ThreadPoolExecutor(max_workers=self._config.workers)

    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        config = self._config
        if config.ip_network:
            if self._thread is None:
                self._start_discovery()

            executor = self._executor
            if executor is None:
                raise RuntimeError("Expected executor be set")

            sent = []
            for host, discovered in list(config.discovered_instances.items()):
                future = executor.submit(self._check_with_config, discovered)
                sent.append(future)
                future.add_done_callback(functools.partial(self._check_config_done, host))
            futures.wait(sent)

            tags = ['network:{}'.format(config.ip_network)]
            tags.extend(config.tags)
            self.gauge('snmp.discovered_devices_count', len(config.discovered_instances), tags=tags)
        else:
            self._check_with_config(config)

    def _check_config_done(self, host, future):
        # type: (str, futures.Future) -> None
        config = self._config
        if future.result():
            config.failing_instances[host] += 1
            if config.failing_instances[host] >= config.allowed_failures:
                # Remove it from discovered instances, we'll re-discover it later if it reappears
                config.discovered_instances.pop(host)
                # Reset the failure counter as well
                config.failing_instances.pop(host)
        else:
            # Reset the counter if not's failing
            config.failing_instances.pop(host, None)

    def _check_with_config(self, config):
        # type: (InstanceConfig) -> Optional[str]
        # Reset errors
        instance = config.instance
        error = results = None
        tags = config.tags
        try:
            if not (config.all_oids or config.bulk_oids):
                sys_object_oid = self.fetch_sysobject_oid(config)
                profile = self._profile_for_sysobject_oid(sys_object_oid)
                config.refresh_with_profile(self.profiles[profile], self.warning)
                config.add_profile_tag(profile)

            if config.all_oids or config.bulk_oids:
                self.log.debug('Querying device %s', config.ip_address)
                config.add_uptime_metric()
                results, error = self.fetch_results(config, config.all_oids, config.bulk_oids)
                tags = self.extract_metric_tags(config.parsed_metric_tags, results)
                tags.extend(config.tags)
                self.report_metrics(config.parsed_metrics, results, tags)
        except CheckException as e:
            error = str(e)
            self.warning(error)
        except Exception as e:
            if not error:
                error = 'Failed to collect metrics for {} - {}'.format(instance['name'], e)
            self.warning(error)
        finally:
            # Report service checks
            status = self.OK  # type: ServiceCheckStatus
            if error:
                status = self.CRITICAL
                if results:
                    status = self.WARNING
            self.service_check(self.SC_STATUS, status, tags=tags, message=error)
        return error

    def extract_metric_tags(self, metric_tags, results):
        # type: (List[ParsedMetricTag], Dict[str, dict]) -> List[str]
        extracted_tags = []
        for tag in metric_tags:
            if tag.symbol not in results:
                self.log.debug('Ignoring tag %s', tag.symbol)
                continue
            tag_values = list(results[tag.symbol].values())
            if len(tag_values) > 1:
                raise CheckException(
                    'You are trying to use a table column (OID `{}`) as a metric tag. This is not supported as '
                    '`metric_tags` can only refer to scalar OIDs.'.format(tag.symbol)
                )
            extracted_tags.append('{}:{}'.format(tag.name, tag_values[0]))
        return extracted_tags

    def report_metrics(
        self,
        metrics,  # type: List[Union[ParsedMetric, ParsedTableMetric]]
        results,  # type: Dict[str, dict]
        tags,  # type: List[str]
    ):
        # type: (...) -> None
        """
        For each of the metrics specified gather the tags requested in the
        instance conf for each row.

        Submit the results to the aggregator.
        """
        for metric in metrics:
            name = metric.name
            if name not in results:
                self.log.debug('Ignoring metric %s', name)
                continue
            if isinstance(metric, ParsedTableMetric):
                for index, val in iteritems(results[name]):
                    metric_tags = tags + self.get_index_tags(index, results, metric.index_tags, metric.column_tags)
                    self.submit_metric(name, val, metric.forced_type, metric_tags)
            else:
                result = list(results[name].items())
                if len(result) > 1:
                    self.log.warning('Several rows corresponding while the metric is supposed to be a scalar')
                    if metric.enforce_scalar:
                        # For backward compatibility reason, we publish the first value for OID.
                        continue
                val = result[0][1]
                metric_tags = tags + metric.metric_tags
                self.submit_metric(name, val, metric.forced_type, metric_tags)

    def get_index_tags(
        self,
        index,  # type: Dict[int, float]
        results,  # type: Dict[str, dict]
        index_tags,  # type: List[Tuple[str, int]]
        column_tags,  # type: List[Tuple[str, str]]
    ):
        # type: (...) -> List[str]
        """
        Gather the tags for this row of the table (index) based on the
        results (all the results from the query).
        index_tags and column_tags are the tags to gather.
         - Those specified in index_tags contain the tag_group name and the
           index of the value we want to extract from the index tuple.
           cf. 1 for ipVersion in the IP-MIB::ipSystemStatsTable for example
         - Those specified in column_tags contain the name of a column, which
           could be a potential result, to use as a tage
           cf. ifDescr in the IF-MIB::ifTable for example
        """
        tags = []  # type: List[str]

        for idx_tag in index_tags:
            tag_group = idx_tag[0]
            try:
                tag_value = index[idx_tag[1] - 1]
            except IndexError:
                self.log.warning('Not enough indexes, skipping tag %s', tag_group)
                continue
            tags.append('{}:{}'.format(tag_group, tag_value))

        for col_tag in column_tags:
            tag_group = col_tag[0]
            try:
                column_value = results[col_tag[1]][index]
            except KeyError:
                self.log.warning('Column %s not present in the table, skipping this tag', col_tag[1])
                continue
            if reply_invalid(column_value):
                self.log.warning("Can't deduct tag from column for tag %s", tag_group)
                continue
            tag_value = column_value.prettyPrint()
            tags.append('{}:{}'.format(tag_group, tag_value))

        return tags

    def submit_metric(self, name, snmp_value, forced_type, tags):
        # type: (str, Any, Optional[str], List[str]) -> None
        """
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator.
        """
        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning('No such Mib available: %s', name)
            return

        metric_name = self.normalize(name, prefix='snmp')

        value = 0.0  # type: float

        if forced_type:
            forced_type = forced_type.lower()
            if forced_type == 'gauge':
                value = int(snmp_value)
                self.gauge(metric_name, value, tags)
            elif forced_type == 'percent':
                value = total_time_to_temporal_percent(int(snmp_value), scale=1)
                self.rate(metric_name, value, tags)
            elif forced_type == 'counter':
                value = int(snmp_value)
                self.rate(metric_name, value, tags)
            elif forced_type == 'monotonic_count':
                value = int(snmp_value)
                self.monotonic_count(metric_name, value, tags)
            else:
                self.warning('Invalid forced-type specified: %s in %s', forced_type, name)
                raise ConfigurationError('Invalid forced-type in config file: {}'.format(name))
            return

        # Ugly hack but couldn't find a cleaner way
        # Proper way would be to use the ASN1 method isSameTypeWith but it
        # wrongfully returns True in the case of CounterBasedGauge64
        # and Counter64 for example
        snmp_class = snmp_value.__class__.__name__
        if snmp_class in SNMP_COUNTERS:
            value = int(snmp_value)
            self.rate(metric_name, value, tags)
            return
        if snmp_class in SNMP_GAUGES:
            value = int(snmp_value)
            self.gauge(metric_name, value, tags)
            return

        if snmp_class == 'Opaque':
            # Try support for floats
            try:
                value = float(pyasn1_decode(bytes(snmp_value))[0])
            except Exception:
                pass
            else:
                self.gauge(metric_name, value, tags)
                return

        # Falls back to try to cast the value.
        try:
            value = float(snmp_value)
        except ValueError:
            pass
        else:
            self.gauge(metric_name, value, tags)
            return

        self.log.warning('Unsupported metric type %s for %s', snmp_class, metric_name)
