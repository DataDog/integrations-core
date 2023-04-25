# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import fnmatch
import functools
import ipaddress
import json
import re
import threading
import time
import weakref
from collections import defaultdict
from concurrent import futures
from typing import Any, DefaultDict, Dict, List, Optional, Pattern, Tuple  # noqa: F401

from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.errors import CheckException
from datadog_checks.snmp.utils import extract_value

from .commands import snmp_bulk, snmp_get, snmp_getnext
from .compat import read_persistent_cache, write_persistent_cache
from .config import InstanceConfig
from .discovery import discover_instances
from .exceptions import PySnmpError
from .metrics import as_metric_with_forced_type, as_metric_with_inferred_type, try_varbind_value_to_float
from .mibs import MIBLoader
from .models import OID
from .parsing import ColumnTag, IndexTag, ParsedMetric, ParsedTableMetric, SymbolTag  # noqa: F401
from .pysnmp_types import ObjectIdentity, ObjectType, noSuchInstance, noSuchObject
from .utils import (
    OIDPrinter,
    batches,
    get_default_profiles,
    get_profile_definition,
    oid_pattern_specificity,
    recursively_expand_base_profiles,
    transform_index,
)

DEFAULT_OID_BATCH_SIZE = 10
LOADER_TAG = 'loader:python'

_MAX_FETCH_NUMBER = 10**6


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
    _thread_factory = threading.Thread  # Store as an attribute for easier mocking.

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(SnmpCheck, self).__init__(*args, **kwargs)

        # Set OID batch size
        self.oid_batch_size = int(self.init_config.get('oid_batch_size', DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = self.init_config.get('mibs_folder')

        self.optimize_mib_memory_usage = is_affirmative(self.init_config.get('optimize_mib_memory_usage', False))

        self.ignore_nonincreasing_oid = is_affirmative(self.init_config.get('ignore_nonincreasing_oid', False))
        self.refresh_oids_cache_interval = int(
            self.init_config.get('refresh_oids_cache_interval', InstanceConfig.DEFAULT_REFRESH_OIDS_CACHE_INTERVAL)
        )

        self.profiles = self._load_profiles()
        self.profiles_by_oid = self._get_profiles_mapping()

        self._config = self._build_config(self.instance)

        self._last_fetch_number = 0

        self._submitted_metrics = 0

    def _get_next_fetch_id(self):
        # type: () -> str
        """
        Return a unique ID that represents a given "fetch results" operation, for logging purposes.

        Note: this is ad-hoc and dinstinct from the 'request-id' as defined by the SNMP protocol.
        """
        self._last_fetch_number += 1

        # Prevent ID from becoming infinitely large.
        self._last_fetch_number %= _MAX_FETCH_NUMBER

        # Include check ID to avoid conflicts between concurrent instances of the check.
        return '{}-{}'.format(self.check_id, self._last_fetch_number)

    def _load_profiles(self):
        # type: () -> Dict[str, Dict[str, Any]]
        """
        Load the configured SNMP profiles.
        """
        configured_profiles = self.init_config.get('profiles')

        if configured_profiles is None:
            return get_default_profiles()

        profiles = {}

        for name, profile in configured_profiles.items():
            try:
                definition = get_profile_definition(profile)
            except Exception as exc:
                raise ConfigurationError("Couldn't read profile '{}': {}".format(name, exc))

            try:
                recursively_expand_base_profiles(definition)
            except Exception as exc:
                raise ConfigurationError("Failed to expand base profiles in profile '{}': {}".format(name, exc))

            profiles[name] = {'definition': definition}

        return profiles

    def _get_profiles_mapping(self):
        # type: () -> Dict[str, str]
        """
        Get the mapping from sysObjectID to profile.
        """
        profiles_by_oid = {}  # type: Dict[str, str]
        for name, profile in self.profiles.items():
            sys_object_oids = profile['definition'].get('sysobjectid')
            if sys_object_oids is None:
                continue
            if isinstance(sys_object_oids, str):
                sys_object_oids = [sys_object_oids]
            for sys_object_oid in sys_object_oids:
                profile_match = profiles_by_oid.get(sys_object_oid)
                if profile_match:
                    raise ConfigurationError(
                        "Profile {} has the same sysObjectID ({}) as {}".format(name, sys_object_oid, profile_match)
                    )
                else:
                    profiles_by_oid[sys_object_oid] = name
        return profiles_by_oid

    def _build_config(self, instance):
        # type: (dict) -> InstanceConfig
        loader = MIBLoader.shared_instance() if self.optimize_mib_memory_usage else MIBLoader()

        return InstanceConfig(
            instance,
            global_metrics=self.init_config.get('global_metrics', []),
            mibs_path=self.mibs_path,
            refresh_oids_cache_interval=self.refresh_oids_cache_interval,
            profiles=self.profiles,
            profiles_by_oid=self.profiles_by_oid,
            loader=loader,
            logger=self.log,
        )

    def _build_autodiscovery_config(self, source_instance, ip_address):
        # type: (dict, str) -> InstanceConfig
        instance = copy.deepcopy(source_instance)
        network_address = instance.pop('network_address')
        instance['ip_address'] = ip_address

        instance.setdefault('tags', [])
        instance['tags'].append('autodiscovery_subnet:{}'.format(network_address))

        return self._build_config(instance)

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

    def fetch_results(
        self, config  # type: InstanceConfig
    ):
        # type: (...) -> Tuple[Dict[str, Dict[Tuple[str, ...], Any]], List[OID], Optional[str]]
        """
        Perform a snmpwalk on the domain specified by the oids, on the device
        configured in instance.

        Returns a dictionary:
        dict[oid/metric_name][row index] = value
        In case of scalar objects, the row index is just 0
        """
        results = defaultdict(dict)  # type: DefaultDict[str, Dict[Tuple[str, ...], Any]]
        enforce_constraints = config.enforce_constraints
        fetch_id = self._get_next_fetch_id()

        all_binds, error = self.fetch_oids(
            config,
            config.oid_config.scalar_oids,
            config.oid_config.next_oids,
            enforce_constraints=enforce_constraints,
            fetch_id=fetch_id,
        )
        for oid in config.oid_config.bulk_oids:
            try:
                oid_object_type = oid.as_object_type()
                self.log.debug(
                    '[%s] Running SNMP command getBulk on OID %s',
                    fetch_id,
                    OIDPrinter((oid_object_type,), with_values=False),
                )
                binds = snmp_bulk(
                    config,
                    oid_object_type,
                    self._NON_REPEATERS,
                    self._MAX_REPETITIONS,
                    enforce_constraints,
                    self.ignore_nonincreasing_oid,
                )
                all_binds.extend(binds)
            except (PySnmpError, CheckException) as e:
                message = '[{}] Failed to collect some metrics: {}'.format(fetch_id, e)
                if not error:
                    error = message
                self.warning(message)

        scalar_oids = []
        for result_oid, value in all_binds:
            oid = OID(result_oid)
            scalar_oids.append(oid)
            match = config.resolve_oid(oid)
            results[match.name][match.indexes] = value
        self.log.debug('[%s] Raw results: %s', fetch_id, OIDPrinter(results, with_values=False))
        # Freeze the result
        results.default_factory = None  # type: ignore
        return results, scalar_oids, error

    def fetch_oids(self, config, scalar_oids, next_oids, enforce_constraints, fetch_id):
        # type: (InstanceConfig, List[OID], List[OID], bool, str) -> Tuple[List[Any], Optional[str]]
        # UPDATE: We used to perform only a snmpgetnext command to fetch metric values.
        # It returns the wrong value when the OID passed is referring to a specific leaf.
        # For example:
        # snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.4.2.1.7.222
        # iso.3.6.1.2.1.25.4.2.1.7.224 = INTEGER: 2
        # SOLUTION: perform a snmpget command and fallback with snmpgetnext if not found
        error = None
        scalar_oids = [oid.as_object_type() for oid in scalar_oids]
        next_oids = [oid.as_object_type() for oid in next_oids]
        all_binds = []

        for oids_batch in batches(scalar_oids, size=self.oid_batch_size):
            try:
                self.log.debug(
                    '[%s] Running SNMP command get on OIDS: %s', fetch_id, OIDPrinter(oids_batch, with_values=False)
                )

                var_binds = snmp_get(config, oids_batch, lookup_mib=enforce_constraints)
                self.log.debug('[%s] Returned vars: %s', fetch_id, OIDPrinter(var_binds, with_values=True))

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
                    next_oids.extend(missing_results)

            except (PySnmpError, CheckException) as e:
                message = '[{}] Failed to collect some metrics: {}'.format(fetch_id, e)
                if not error:
                    error = message
                self.warning(message)

        for oids_batch in batches(next_oids, size=self.oid_batch_size):
            try:
                self.log.debug(
                    '[%s] Running SNMP command getNext on OIDS: %s', fetch_id, OIDPrinter(oids_batch, with_values=False)
                )
                binds = list(
                    snmp_getnext(
                        config,
                        oids_batch,
                        lookup_mib=enforce_constraints,
                        ignore_nonincreasing_oid=self.ignore_nonincreasing_oid,
                    )
                )
                self.log.debug('[%s] Returned vars: %s', fetch_id, OIDPrinter(binds, with_values=True))
                all_binds.extend(binds)

            except (PySnmpError, CheckException) as e:
                message = '[{}] Failed to collect some metrics: {}'.format(fetch_id, e)
                if not error:
                    error = message
                self.warning(message)

        return all_binds, error

    def fetch_sysobject_oid(self, config):
        # type: (InstanceConfig) -> str
        """Return the sysObjectID of the instance."""
        # Reference sysObjectID directly, see http://oidref.com/1.3.6.1.2.1.1.2
        oid = ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 1, 2, 0)))
        self.log.debug('Running SNMP command on OID: %s', OIDPrinter((oid,), with_values=False))
        var_binds = snmp_get(config, [oid], lookup_mib=False)
        self.log.debug('Returned vars: %s', OIDPrinter(var_binds, with_values=True))
        return var_binds[0][1].prettyPrint()

    def _profile_for_sysobject_oid(self, sys_object_oid):
        # type: (str) -> str
        """
        Return the most specific profile that matches the given sysObjectID.
        """
        matched_profiles_by_oid = {
            oid: self.profiles_by_oid[oid] for oid in self.profiles_by_oid if fnmatch.fnmatch(sys_object_oid, oid)
        }

        if not matched_profiles_by_oid:
            raise ConfigurationError('No profile matching sysObjectID {}'.format(sys_object_oid))

        oid = max(matched_profiles_by_oid.keys(), key=lambda oid: oid_pattern_specificity(oid))

        return matched_profiles_by_oid[oid]

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
                self._config.discovered_instances[host] = self._build_autodiscovery_config(self.instance, host)

        raw_discovery_interval = self._config.instance.get('discovery_interval', 3600)
        try:
            discovery_interval = float(raw_discovery_interval)
        except (ValueError, TypeError):
            message = 'discovery_interval could not be parsed as a number: {!r}'.format(raw_discovery_interval)
            raise ConfigurationError(message)

        # Pass a weakref to the discovery function to not have a reference cycle
        self._thread = self._thread_factory(
            target=discover_instances, args=(self._config, discovery_interval, weakref.ref(self)), name=self.name
        )
        self._thread.daemon = True
        self._thread.start()
        self._executor = futures.ThreadPoolExecutor(max_workers=self._config.workers)

    def check(self, _):
        # type: (Dict[str, Any]) -> None
        start_time = time.time()
        self._submitted_metrics = 0
        config = self._config

        if config.ip_network:
            if self._thread is None:
                self._start_discovery()

            executor = self._executor
            if executor is None:
                raise RuntimeError("Expected executor be set")

            sent = []
            for host, discovered in list(config.discovered_instances.items()):
                future = executor.submit(self._check_device, discovered)  # type: Any
                sent.append(future)
                future.add_done_callback(functools.partial(self._on_check_device_done, host))
            futures.wait(sent)

            tags = ['network:{}'.format(config.ip_network), 'autodiscovery_subnet:{}'.format(config.ip_network)]
            tags.extend(config.tags)
            self.gauge('snmp.discovered_devices_count', len(config.discovered_instances), tags=tags)
        else:
            error, tags = self._check_device(config)
            # no need to handle error here since it's already handled inside `self._check_device`

        self.submit_telemetry_metrics(start_time, tags)

    def submit_telemetry_metrics(self, start_time, tags):
        # type: (float, List[str]) -> None
        telemetry_tags = tags + [LOADER_TAG]
        # Performance Metrics
        # - for single device, tags contain device specific tags
        # - for network, tags contain network tags, but won't contain individual device tags
        check_duration = time.time() - start_time
        self.monotonic_count('datadog.snmp.check_interval', time.time(), tags=telemetry_tags)
        self.gauge('datadog.snmp.check_duration', check_duration, tags=telemetry_tags)
        self.gauge('datadog.snmp.submitted_metrics', self._submitted_metrics, tags=telemetry_tags)

    def _on_check_device_done(self, host, future):
        # type: (str, futures.Future) -> None
        config = self._config
        error, _ = future.result()
        if error:
            config.failing_instances[host] += 1
            if config.failing_instances[host] >= config.allowed_failures:
                # Remove it from discovered instances, we'll re-discover it later if it reappears
                config.discovered_instances.pop(host)
                # Reset the failure counter as well
                config.failing_instances.pop(host)
        else:
            # Reset the counter if not's failing
            config.failing_instances.pop(host, None)

    def _check_device(self, config):
        # type: (InstanceConfig) -> Tuple[Optional[str], List[str]]
        # Reset errors
        if config.device is None:
            raise RuntimeError('No device set')  # pragma: no cover

        instance = config.instance
        error = results = None
        tags = config.tags
        if config.oid_config.should_reset():
            config.oid_config.reset()
        try:
            if not config.oid_config.has_oids():
                sys_object_oid = self.fetch_sysobject_oid(config)
                profile = self._profile_for_sysobject_oid(sys_object_oid)
                config.refresh_with_profile(self.profiles[profile])
                config.add_profile_tag(profile)

            if config.oid_config.has_oids():
                self.log.debug('Querying %s', config.device)
                config.add_uptime_metric()
                results, scalar_oids, error = self.fetch_results(config)
                config.oid_config.update_scalar_oids(scalar_oids)
                tags = self.extract_metric_tags(config.parsed_metric_tags, results)
                tags.extend(config.tags)
                self.report_metrics(config.parsed_metrics, results, tags)
        except CheckException as e:
            error = str(e)
            self.warning(error)
        except Exception as e:
            if not error:
                error = 'Failed to collect metrics for {} - {}'.format(self._get_instance_name(instance), e)
            self.log.debug(error, exc_info=True)
            self.warning(error)
        finally:
            # At this point, `tags` might include some extra tags added in try clause

            # Sending `snmp.devices_monitored` with value 1 will allow users to count devices
            # by using `sum by {X}` queries in UI. X being a tag like `autodiscovery_subnet`, `snmp_profile`, etc
            self.gauge('snmp.devices_monitored', 1, tags=tags + [LOADER_TAG])

            # Report service checks
            status = self.OK
            if error:
                status = self.CRITICAL
                if results:
                    status = self.WARNING
            self.service_check(self.SC_STATUS, status, tags=tags, message=error)
        return error, tags

    def extract_metric_tags(self, metric_tags, results):
        # type: (List[SymbolTag], Dict[str, dict]) -> List[str]
        extracted_tags = []  # type: List[str]
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
            try:
                extracted_tags.extend(tag.parsed_metric_tag.matched_tags(tag_values[0]))
            except re.error as e:
                self.log.debug('Failed to match %s for %s: %s', tag_values[0], tag.symbol, e)
        return extracted_tags

    def report_metrics(
        self,
        metrics,  # type: List[ParsedMetric]
        results,  # type: Dict[str, Dict[Tuple[str, ...], Any]]
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
                    self.submit_metric(
                        name, val, metric.forced_type, metric_tags, metric.options, metric.extract_value_pattern
                    )
                    self.try_submit_bandwidth_usage_metric_if_bandwidth_metric(name, index, results, metric_tags)
            else:
                result = list(results[name].items())
                if len(result) > 1:
                    self.log.warning('Several rows corresponding while the metric is supposed to be a scalar')
                    if metric.enforce_scalar:
                        # For backward compatibility reason, we publish the first value for OID.
                        continue
                val = result[0][1]
                metric_tags = tags + metric.tags
                self.submit_metric(
                    name, val, metric.forced_type, metric_tags, metric.options, metric.extract_value_pattern
                )

    BANDWIDTH_METRIC_NAME_TO_BANDWIDTH_USAGE_METRIC_NAME_MAPPING = {
        'ifHCInOctets': 'ifBandwidthInUsage',
        'ifHCOutOctets': 'ifBandwidthOutUsage',
    }

    @staticmethod
    def is_bandwidth_metric(name):
        # type: (str) -> bool
        return name in SnmpCheck.BANDWIDTH_METRIC_NAME_TO_BANDWIDTH_USAGE_METRIC_NAME_MAPPING

    def try_submit_bandwidth_usage_metric_if_bandwidth_metric(
        self,
        name,  # type: str
        index,  # type: Tuple[str, ...]
        results,  # type: Dict[str, Dict[Tuple[str, ...], Any]]
        tags,  # type: List[str]
    ):
        # type: (...) -> None
        """
        Safely send bandwidth usage metrics if name is a bandwidth metric
        """
        try:
            self.submit_bandwidth_usage_metric_if_bandwidth_metric(name, index, results, tags)
        except Exception as e:
            msg = 'Unable submit bandwidth usage metric with name=`{}`, index=`{}`, tags=`{}`: {}'.format(
                name, index, tags, e
            )
            self.log.warning(msg)
            self.log.debug(msg, exc_info=True)

    def submit_bandwidth_usage_metric_if_bandwidth_metric(
        self,
        name,  # type: str
        index,  # type: Tuple[str, ...]
        results,  # type: Dict[str, Dict[Tuple[str, ...], Any]]
        tags,  # type: List[str]
    ):
        # type: (...) -> None
        """
        Evaluate and report input/output bandwidth usage. If any of `ifHCInOctets`, `ifHCOutOctets`  or `ifHighSpeed`
        is missing then bandwidth will not be reported.

        Bandwidth usage is:

        interface[In|Out]Octets(t+dt) - interface[In|Out]Octets(t)
        ----------------------------------------------------------
                        dt*interfaceSpeed

        Given:
        * ifHCInOctets: the total number of octets received on the interface.
        * ifHCOutOctets: The total number of octets transmitted out of the interface.
        * ifHighSpeed: An estimate of the interface's current bandwidth in Mb/s (10^6 bits
                       per second). It is constant in time, can be overwritten by the system admin.
                       It is the total available bandwidth.
        Bandwidth usage is evaluated as: ifHC[In|Out]Octets/ifHighSpeed and reported as *rate*
        """
        if not self.is_bandwidth_metric(name):
            return

        if 'ifHighSpeed' not in results:
            self.log.debug('[SNMP Bandwidth usage] missing `ifHighSpeed` metric, skipping metric %s', name)
            return

        if name not in results:
            self.log.debug('[SNMP Bandwidth usage] missing `%s` metric, skipping this row. index=%s', name, index)
            return

        octets_value = results[name][index]
        try:
            if_high_speed_val = results['ifHighSpeed'][index]
        except KeyError:
            self.log.debug('[SNMP Bandwidth usage] missing `ifHighSpeed` metric, skipping this row. ' 'index=%s', index)
            return

        if_high_speed = try_varbind_value_to_float(if_high_speed_val)
        if if_high_speed is None:
            err_msg = 'Metric: {} has non float value: {}. Only float values can be submitted as metrics.'.format(
                repr(name), repr(if_high_speed_val)
            )
            self.log.debug(err_msg, exc_info=True)
            return

        bits_value = try_varbind_value_to_float(octets_value) * 8
        if bits_value is None:
            err_msg = 'Metric: {} has non float value: {}. Only float values can be submitted as metrics.'.format(
                repr(name), repr(octets_value)
            )
            self.log.debug(err_msg, exc_info=True)
            return

        try:
            bandwidth_usage_value = (bits_value / (if_high_speed * (10**6))) * 100
        except ZeroDivisionError:
            self.log.debug('Zero value at ifHighSpeed, skipping this row. index=%s', index)
            return

        self.rate(
            "snmp.{}.rate".format(SnmpCheck.BANDWIDTH_METRIC_NAME_TO_BANDWIDTH_USAGE_METRIC_NAME_MAPPING[name]),
            bandwidth_usage_value,
            tags,
        )
        self._submitted_metrics += 1

    def get_index_tags(
        self,
        index,  # type: Tuple[str, ...]
        results,  # type: Dict[str, dict]
        index_tags,  # type: List[IndexTag]
        column_tags,  # type: List[ColumnTag]
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
           could be a potential result, to use as a tag
           cf. ifDescr in the IF-MIB::ifTable for example
        """
        tags = []  # type: List[str]

        for index_tag in index_tags:
            raw_index_value = index_tag.index
            try:
                value = index[raw_index_value - 1]
            except IndexError:
                self.log.warning('Not enough indexes, skipping index %s', raw_index_value)
                continue
            tags.extend(index_tag.parsed_metric_tag.matched_tags(value))

        for column_tag in column_tags:
            raw_column_value = column_tag.column
            self.log.trace(
                'Processing column tag: raw_column_value=%s index_slices=%s', raw_column_value, column_tag.index_slices
            )
            if column_tag.index_slices:
                new_index = transform_index(index, column_tag.index_slices)
            else:
                new_index = index
            self.log.trace('Processing column tag: new_index=%s old_index=%s', new_index, index)
            if new_index is None:
                continue
            try:
                column_value = results[raw_column_value][new_index]
            except KeyError:
                self.log.debug(
                    'Column `%s not present in the table, skipping this tag. index=%s', raw_column_value, new_index
                )
                continue
            if reply_invalid(column_value):
                self.log.warning("Can't deduct tag from column %s", column_tag.column)
                continue
            value = column_value.prettyPrint()
            tags.extend(column_tag.parsed_metric_tag.matched_tags(value))
        return tags

    def monotonic_count_and_rate(self, metric, value, tags):
        # type: (str, Any, List[str]) -> None
        """Specific submission method which sends a metric both as a monotonic count and a rate."""
        self.monotonic_count(metric, value, tags=tags)
        self.rate("{}.rate".format(metric), value, tags=tags)

    def submit_metric(self, name, snmp_value, forced_type, tags, options, extract_value_pattern):
        # type: (str, Any, Optional[str], List[str], dict, Optional[Pattern]) -> None
        """
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator.
        """
        try:
            self._do_submit_metric(name, snmp_value, forced_type, tags, options, extract_value_pattern)
        except Exception as e:
            msg = (
                'Unable to submit metric `{}` with '
                'value=`{}` ({}), forced_type=`{}`, tags=`{}`, options=`{}`, extract_value_pattern=`{}`: {}'.format(
                    name, snmp_value, type(snmp_value), forced_type, tags, options, extract_value_pattern, e
                )
            )
            self.log.warning(msg)
            self.log.debug(msg, exc_info=True)

    def _do_submit_metric(self, name, snmp_value, forced_type, tags, options, extract_value_pattern):
        # type: (str, Any, Optional[str], List[str], dict, Optional[Pattern]) -> None

        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning('No such Mib available: %s', name)
            return

        if 'metric_suffix' in options:
            metric_name = self.normalize('{}.{}'.format(name, options['metric_suffix']), prefix='snmp')
        else:
            metric_name = self.normalize(name, prefix='snmp')

        if extract_value_pattern:
            snmp_value = extract_value(extract_value_pattern, snmp_value.prettyPrint())

        if forced_type is not None:
            metric = as_metric_with_forced_type(snmp_value, forced_type, options)
        else:
            metric = as_metric_with_inferred_type(snmp_value)

        if metric is None:
            raise RuntimeError('Unsupported metric type {} for {}'.format(type(snmp_value), metric_name))

        submit_func = getattr(self, metric['type'])
        submit_func(metric_name, metric['value'], tags=tags)

        if metric['type'] == 'monotonic_count_and_rate':
            self._submitted_metrics += 1
        self._submitted_metrics += 1
