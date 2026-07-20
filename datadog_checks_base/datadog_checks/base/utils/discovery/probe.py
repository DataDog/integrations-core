from __future__ import annotations

import copy
import dataclasses
import importlib
import logging
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from datadog_checks.base.config import is_affirmative
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.format import json

if TYPE_CHECKING:
    from datadog_checks.base.checks.base import AgentCheck
    from datadog_checks.base.utils.discovery import Service


def _pkg(cls: type) -> str | None:
    parts = cls.__module__.split('.')
    if len(parts) >= 2 and parts[0] == 'datadog_checks':
        return parts[1]
    return None


def _discovery_check_name(cls: type[AgentCheck]) -> str:
    return _pkg(cls) or cls.__name__


def generated_discovery_candidates(cls: type[AgentCheck], service: Service) -> Iterable[dict[str, Any]]:
    if (package := _pkg(cls)) is None:
        return ()

    module_name = f'datadog_checks.{package}.config_models.discovery'
    try:
        discovery = importlib.import_module(module_name)
    except ImportError as e:
        # Two shapes of "not opted in":
        #   1. config_models/discovery.py missing → e.name == module_name
        #   2. config_models/ package missing     → e.name is a shorter prefix
        # Both satisfy startswith. e.name being an unrelated module (a real
        # broken dependency inside discovery.py) does not, so it re-raises.
        if e.name and module_name.startswith(e.name):
            return ()
        raise

    # This function is expected to examine the attributes of the provided
    # service (ports, host, etc.) and return an iterator which yields
    # appropriate candidate configurations (for example, `{init_config: {},
    # instances: [{"endpoint": "http://host:1234"}]}`).
    return discovery.candidates(service)


def _parse_service_json(service_json: str) -> Service:
    from datadog_checks.base.utils.discovery import Service

    return Service.model_validate_json(service_json)


@dataclasses.dataclass
class _DiscoveryRunStats:
    metric_count: int = 0


class _DiscoveryAggregatorProxy:
    def __init__(self, stats: _DiscoveryRunStats) -> None:
        self._stats = stats

    def submit_metric(self, *args: Any, **kwargs: Any) -> None:
        self._stats.metric_count += 1

    def submit_histogram_bucket(self, *args: Any, **kwargs: Any) -> None:
        self._stats.metric_count += 1

    def submit_event(self, *args: Any, **kwargs: Any) -> None:
        pass

    def submit_service_check(self, *args: Any, **kwargs: Any) -> None:
        pass

    def submit_event_platform_event(self, *args: Any, **kwargs: Any) -> None:
        pass


class _DiscoveryErrorDowngrade(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.ERROR:
            record.levelno = logging.DEBUG
            record.levelname = 'DEBUG'
        return True


def _discovery_noop(*args: Any, **kwargs: Any) -> None:
    pass


@contextmanager
def _suppress_discovery_side_effects(check: AgentCheck) -> Iterator[_DiscoveryRunStats]:
    noop_methods = (
        'send_log',
        'service_metadata',
        'set_external_tags',
        'set_metadata',
        'write_persistent_cache',
    )
    originals: dict[str, Any] = {}
    stats = _DiscoveryRunStats()

    check._discovery_aggregator = _DiscoveryAggregatorProxy(stats)  # type: ignore[attr-defined]

    for method in noop_methods:
        if hasattr(check, method):
            originals[method] = getattr(check, method)
            setattr(check, method, _discovery_noop)

    # Attach the downgrade filter to a dedicated child logger and point check.log at it.
    # This scopes suppression to records that flow through check.log during this run — including
    # any threads spawned by check.run() that log via the same adapter — without touching the
    # shared class-level logger that concurrent real check instances also use.
    log_adapter = getattr(check, 'log', None)
    shared_logger = getattr(log_adapter, 'logger', None)
    if shared_logger is not None:
        discovery_logger = logging.getLogger(shared_logger.name + '._discovery')
        log_filter = _DiscoveryErrorDowngrade()
        discovery_logger.addFilter(log_filter)
        log_adapter.logger = discovery_logger

    try:
        yield stats
    finally:
        if shared_logger is not None:
            log_adapter.logger = shared_logger
            discovery_logger.removeFilter(log_filter)
        del check._discovery_aggregator  # type: ignore[attr-defined]
        for method, original in originals.items():
            setattr(check, method, original)


def _try_discovery_candidate(cls: type[AgentCheck], check_name: str, candidate: Any) -> list[dict[str, Any]] | None:
    if not isinstance(candidate, dict):
        raise ConfigurationError('config-discovery: generated candidate must be a mapping')

    # candidates() yields a fresh dict on every iteration; no copy needed for the returned config.
    config = candidate
    init_config = config.setdefault('init_config', {})
    instances = config.setdefault('instances', [])

    if not isinstance(init_config, dict):
        raise ConfigurationError('config-discovery: generated init_config must be a mapping')
    if not isinstance(instances, list):
        raise ConfigurationError('config-discovery: generated instances must be a list')
    if not instances:
        raise ConfigurationError('config-discovery: generated candidate has no instances')
    # Only single-instance candidates are validated: check.run() evaluates self.instances[0],
    # so additional instances would be accepted without validation.
    if len(instances) > 1:
        raise ConfigurationError('config-discovery: multi-instance candidates are not supported')
    # process_isolation routes submissions through run_with_isolation(), which passes the
    # module-level aggregator directly and therefore bypasses _DiscoveryAggregatorProxy.
    if is_affirmative(init_config.get('process_isolation', False)) or any(
        is_affirmative(inst.get('process_isolation', False)) for inst in instances if isinstance(inst, dict)
    ):
        raise ConfigurationError('config-discovery: process_isolation is not supported during discovery')

    init_config, instances = copy.deepcopy((config['init_config'], config['instances']))
    check = cls(check_name, init_config, instances)
    with _suppress_discovery_side_effects(check) as stats:
        error_report = check.run()

    if not error_report and stats.metric_count > 0:
        return [config]
    return None


def run_discovery(cls: type[AgentCheck], service_json: str) -> str:
    """Entry point called by AgentCheck.discover_config.

    A candidate is accepted only if the real check collected at least one metric
    (``stats.metric_count > 0``). Integrations whose only discovery signal is a
    service check are therefore not discoverable by this criterion; this is a
    known limitation.
    """
    log = logging.getLogger(__name__)

    try:
        service = _parse_service_json(service_json)
    except Exception:
        log.debug('config-discovery: could not parse service payload', exc_info=True)
        return '[]'

    check_name = _discovery_check_name(cls)

    try:
        candidates = cls.generate_configs(service)
    except Exception:
        log.warning('config-discovery: generate_configs failed for %s', check_name, exc_info=True)
        return '[]'

    try:
        for candidate in candidates:
            try:
                result = _try_discovery_candidate(cls, check_name, candidate)
                if result is not None:
                    return json.encode(result)
                log.debug('config-discovery: candidate rejected (no metrics collected)')
            except ConfigurationError:
                log.debug('config-discovery: candidate rejected', exc_info=True)
            except Exception:
                log.warning('config-discovery: candidate raised unexpected error for %s', check_name, exc_info=True)
    except Exception:
        log.warning('config-discovery: generate_configs iteration failed for %s', check_name, exc_info=True)

    return '[]'
