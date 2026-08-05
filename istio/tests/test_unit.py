# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper
from datadog_checks.base.errors import CheckException
from datadog_checks.istio import Istio
from datadog_checks.istio.check import IstioCheckV2
from datadog_checks.istio.constants import BLACKLIST_LABELS
from datadog_checks.istio.legacy_1_4 import LegacyIstioCheck_1_4
from datadog_checks.istio.metrics import (
    CITADEL_METRICS,
    GALLEY_METRICS,
    ISTIOD_METRICS,
    ISTIOD_VERSION,
    MESH_METRICS,
    MIXER_METRICS,
    NON_CONFORMING_METRICS,
    PILOT_METRICS,
    construct_metrics_config,
)

pytestmark = pytest.mark.unit


def _entries_for(metrics, key):
    return [next(iter(cfg.values())) for cfg in metrics if key in cfg]


# --- metrics.py: construct_metrics_config ---


def test_metrics_config_pair_uses_native_dynamic_and_drops_total_entry():
    # Guards the _total-suffix stripping/native_dynamic logic in construct_metrics_config, which
    # every scraper config built by check.py and legacy_1_4.py relies on.
    metrics = construct_metrics_config(
        {
            'go_memstats_alloc_bytes': 'go.memstats.alloc_bytes',
            'go_memstats_alloc_bytes_total': 'go.memstats.alloc_bytes_total',
        }
    )
    assert metrics == [{'go_memstats_alloc_bytes': {'name': 'go.memstats.alloc_bytes', 'type': 'native_dynamic'}}]


def test_metrics_config_lone_total_is_stripped_and_has_no_explicit_type():
    metrics = construct_metrics_config({'foo_bar_total': 'foo.bar_total'})
    assert metrics == [{'foo_bar': {'name': 'foo.bar'}}]


def test_metrics_config_non_total_only_metric_is_passed_through():
    metrics = construct_metrics_config({'foo_bar': 'foo.bar'})
    assert metrics == [{'foo_bar': {'name': 'foo.bar'}}]


def test_metrics_config_non_conforming_total_is_preserved():
    non_conforming = NON_CONFORMING_METRICS[0]
    metrics = construct_metrics_config({non_conforming: 'preserved.name_total'})
    assert metrics == [{non_conforming: {'name': 'preserved.name_total'}}]


def test_metrics_config_pair_where_total_is_non_conforming_is_not_dynamic():
    non_conforming = NON_CONFORMING_METRICS[0]
    base = non_conforming[:-6]
    metrics = construct_metrics_config({base: 'base.name', non_conforming: 'base.name_total'})
    assert _entries_for(metrics, base) == [{'name': 'base.name'}]
    assert _entries_for(metrics, non_conforming) == [{'name': 'base.name_total'}]


def test_metrics_config_multiple_pairs_are_each_dynamic():
    metrics = construct_metrics_config({'a': 'a', 'a_total': 'a_total', 'b': 'b', 'b_total': 'b_total'})
    assert {'a': {'name': 'a', 'type': 'native_dynamic'}} in metrics
    assert {'b': {'name': 'b', 'type': 'native_dynamic'}} in metrics
    assert not any('a_total' in cfg or 'b_total' in cfg for cfg in metrics)


# --- check.py: IstioCheckV2 ---


def test_v2_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:21 (DEFAULT_METRIC_LIMIT 0 -> 1).
    assert IstioCheckV2.DEFAULT_METRIC_LIMIT == 0


def test_v2_sidecar_mode_raises_without_any_endpoint():
    check = IstioCheckV2('istio', {}, [{}])
    with pytest.raises(ConfigurationError, match="Must specify at least one"):
        check._parse_config()


def test_v2_sidecar_mesh_only_builds_single_scraper_with_mesh_namespace():
    check = IstioCheckV2('istio', {}, [{'istio_mesh_endpoint': 'http://mesh/metrics'}])
    check._parse_config()
    assert len(check.scraper_configs) == 1
    assert check.scraper_configs[0]['namespace'] == 'istio.mesh'
    assert check.scraper_configs[0]['openmetrics_endpoint'] == 'http://mesh/metrics'


def test_v2_sidecar_istiod_only_builds_single_scraper_with_default_namespace():
    check = IstioCheckV2('istio', {}, [{'istiod_endpoint': 'http://istiod/metrics'}])
    check._parse_config()
    assert len(check.scraper_configs) == 1
    assert check.scraper_configs[0]['namespace'] == 'istio'
    assert check.scraper_configs[0]['openmetrics_endpoint'] == 'http://istiod/metrics'


def test_v2_sidecar_both_endpoints_build_two_scrapers():
    check = IstioCheckV2(
        'istio', {}, [{'istio_mesh_endpoint': 'http://mesh/metrics', 'istiod_endpoint': 'http://istiod/metrics'}]
    )
    check._parse_config()
    assert len(check.scraper_configs) == 2


def test_v2_invalid_istio_mode_raises_naming_the_mode():
    check = IstioCheckV2('istio', {}, [{'istio_mode': 'bogus', 'istiod_endpoint': 'http://istiod/metrics'}])
    with pytest.raises(ConfigurationError, match="Invalid istio_mode 'bogus'"):
        check._parse_config()


def test_v2_istio_mode_ambient_check_is_lexicographic_equality_not_ordering():
    # Kills the core/ReplaceComparisonOperator_Eq_LtE mutant at check.py:42 (`istio_mode == "ambient"`
    # weakened to `<=`): "a" sorts before "ambient", so the mutant would wrongly take the ambient
    # branch (and raise a different error) instead of reporting an invalid mode.
    check = IstioCheckV2('istio', {}, [{'istio_mode': 'a'}])
    with pytest.raises(ConfigurationError, match="Invalid istio_mode 'a'"):
        check._parse_config()


def test_v2_istio_mode_sidecar_check_is_lexicographic_equality_not_ordering():
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at check.py:44 (`istio_mode == "sidecar"`
    # weakened to `>=`): "zzz" sorts after "sidecar", so the mutant would wrongly take the sidecar
    # branch (and raise a different error) instead of reporting an invalid mode.
    check = IstioCheckV2('istio', {}, [{'istio_mode': 'zzz'}])
    with pytest.raises(ConfigurationError, match="Invalid istio_mode 'zzz'"):
        check._parse_config()


def test_v2_istio_mode_ambient_check_uses_value_equality_not_identity():
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at check.py:42 (`istio_mode == "ambient"`
    # weakened to `is`): a non-interned "ambient" string (built via slicing, not a literal) is `==`
    # but not `is` the "ambient" literal in check.py, so the mutant would wrongly skip this branch.
    istio_mode = 'ambientx'[:-1]
    check = IstioCheckV2('istio', {}, [{'istio_mode': istio_mode, 'ztunnel_endpoint': 'http://ztunnel/metrics'}])
    check._parse_config()
    assert check.scraper_configs[0]['namespace'] == 'istio.ztunnel'


def test_v2_istio_mode_sidecar_check_uses_value_equality_not_identity():
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at check.py:44 (`istio_mode == "sidecar"`
    # weakened to `is`): a non-interned "sidecar" string (built via slicing, not a literal) is `==`
    # but not `is` the "sidecar" literal in check.py, so the mutant would wrongly skip this branch.
    istio_mode = 'sidecarx'[:-1]
    check = IstioCheckV2('istio', {}, [{'istio_mode': istio_mode, 'istiod_endpoint': 'http://istiod/metrics'}])
    check._parse_config()
    assert check.scraper_configs[0]['namespace'] == 'istio'


def test_v2_ambient_mode_without_any_endpoint_raises():
    check = IstioCheckV2('istio', {}, [{'istio_mode': 'ambient'}])
    with pytest.raises(ConfigurationError, match="In ambient mode, must specify at least one of"):
        check._parse_config()


def test_v2_ambient_auto_detected_from_ztunnel_endpoint_without_explicit_mode():
    check = IstioCheckV2('istio', {}, [{'ztunnel_endpoint': 'http://ztunnel/metrics'}])
    check._parse_config()
    assert check.scraper_configs[0]['namespace'] == 'istio.ztunnel'


def test_v2_ambient_ztunnel_defaults_to_use_latest_spec_true_without_warning(caplog):
    check = IstioCheckV2('istio', {}, [{'istio_mode': 'ambient', 'ztunnel_endpoint': 'http://ztunnel/metrics'}])
    with caplog.at_level('WARNING'):
        check._parse_config()
    assert check.scraper_configs[0]['use_latest_spec'] is True
    assert 'use_latest_spec: false' not in caplog.text


def test_v2_ambient_ztunnel_opt_out_of_use_latest_spec_warns():
    check = IstioCheckV2(
        'istio',
        {},
        [{'istio_mode': 'ambient', 'ztunnel_endpoint': 'http://ztunnel/metrics', 'use_latest_spec': False}],
    )
    with mock.patch.object(check, 'log') as log:
        check._parse_config()
    log.warning.assert_called_once()


def test_v2_ambient_waypoint_only_builds_scraper_with_waypoint_namespace():
    check = IstioCheckV2('istio', {}, [{'istio_mode': 'ambient', 'waypoint_endpoint': 'http://waypoint/metrics'}])
    check._parse_config()
    assert len(check.scraper_configs) == 1
    assert check.scraper_configs[0]['namespace'] == 'istio.waypoint'


def test_v2_ambient_all_three_endpoints_build_three_scrapers_including_control_plane():
    check = IstioCheckV2(
        'istio',
        {},
        [
            {
                'istio_mode': 'ambient',
                'ztunnel_endpoint': 'http://ztunnel/metrics',
                'waypoint_endpoint': 'http://waypoint/metrics',
                'istiod_endpoint': 'http://istiod/metrics',
            }
        ],
    )
    check._parse_config()
    namespaces = {config['namespace'] for config in check.scraper_configs}
    assert namespaces == {'istio.ztunnel', 'istio.waypoint', 'istio'}


def test_v2_generate_config_appends_istiod_version_and_uses_given_namespace():
    check = IstioCheckV2('istio', {}, [{'namespace': 'wrong-namespace-should-not-be-used'}])
    config = check._generate_config('http://ep/metrics', {'foo': 'bar'}, 'expected-namespace')
    assert config['openmetrics_endpoint'] == 'http://ep/metrics'
    assert config['metrics'] == [{'foo': {'name': 'bar'}}, ISTIOD_VERSION]
    # The per-call namespace must win even though self.instance carries a different 'namespace'.
    assert config['namespace'] == 'expected-namespace'


def test_v2_generate_config_scraper_defaults_must_be_passed_as_keyword():
    # Kills the core/ReplaceBinaryOperator mutant at check.py:103 (`*` -> `/` in the keyword-only
    # marker): a positional 4th argument must raise TypeError, not be silently accepted.
    check = IstioCheckV2('istio', {}, [{}])
    with pytest.raises(TypeError):
        check._generate_config('http://ep/metrics', {}, 'ns', {'use_latest_spec': True})


def test_v2_create_scraper_returns_openmetrics_compatibility_scraper():
    check = IstioCheckV2('istio', {}, [{}])
    config = {'openmetrics_endpoint': 'http://ep/metrics', 'metrics': [], 'namespace': 'istio'}
    assert isinstance(check.create_scraper(config), OpenMetricsCompatibilityScraper)


def test_v2_get_config_with_defaults_preserves_metrics_and_namespace():
    check = IstioCheckV2('istio', {}, [{}])
    config = {'openmetrics_endpoint': 'http://ep/metrics', 'metrics': [{'foo': {'name': 'bar'}}], 'namespace': 'istio'}
    merged = check.get_config_with_defaults(config)
    assert merged['metrics'] == [{'foo': {'name': 'bar'}}]
    assert merged['namespace'] == 'istio'
    assert merged['openmetrics_endpoint'] == 'http://ep/metrics'


# --- istio.py: Istio dispatcher (legacy v1 entrypoint) ---


def test_v1_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at istio.py:17 (DEFAULT_METRIC_LIMIT 0 -> 1).
    assert Istio.DEFAULT_METRIC_LIMIT == 0


def test_v1_routes_to_v2_when_use_openmetrics_is_truthy():
    check = Istio('istio', {}, [{'istiod_endpoint': 'http://istiod/metrics', 'use_openmetrics': True}])
    assert isinstance(check, IstioCheckV2)


def test_v1_default_use_openmetrics_is_false():
    # Kills the core/ReplaceFalseWithTrue mutant at istio.py:47 (the `False` default for
    # `use_openmetrics`): omitting the key must not silently route to the V2 implementation.
    check = Istio('istio', {}, [{'mixer_endpoint': 'http://mixer/metrics'}])
    assert not isinstance(check, IstioCheckV2)


def test_v1_routes_to_legacy_when_istiod_endpoint_absent():
    check = Istio('istio', {}, [{'mixer_endpoint': 'http://mixer/metrics'}])
    assert isinstance(check, LegacyIstioCheck_1_4)


def test_v1_routes_to_plain_istio_when_istiod_endpoint_present():
    check = Istio('istio', {}, [{'istiod_endpoint': 'http://istiod/metrics'}])
    assert type(check) is Istio


def test_v1_new_uses_first_instance_to_decide_routing():
    # Kills the core/NumberReplacer mutant at istio.py:45 (`instances[0]` -> `instances[-1]` in
    # __new__): routing must be decided by the first instance, not the last.
    check = Istio(
        'istio',
        {},
        [
            {'mixer_endpoint': 'http://mixer/metrics'},
            {'istiod_endpoint': 'http://istiod/metrics', 'use_openmetrics': True},
        ],
    )
    assert isinstance(check, LegacyIstioCheck_1_4)


def test_v1_init_uses_first_instance_for_prometheus_url():
    # Kills the core/NumberReplacer mutant at istio.py:20 (`instances[0]` -> `instances[-1]` in
    # __init__): the config built for the running instance must come from instances[0].
    instance_a = {'istiod_endpoint': 'http://first/metrics'}
    # instance_b already has a valid scraper config so the base class's per-instance validation
    # loop doesn't fail regardless of which instance Istio.__init__ decides to transform.
    instance_b = {
        'istiod_endpoint': 'http://second/metrics',
        'prometheus_url': 'http://second/metrics',
        'metrics': [],
        'namespace': 'istio',
    }
    check = Istio('istio', {}, [instance_a, instance_b])
    assert check.instance is instance_a
    assert check.instance.get('prometheus_url') == 'http://first/metrics'


def test_v1_raises_when_istio_mesh_endpoint_configured_alongside_istiod():
    with pytest.raises(ConfigurationError, match="istio_mesh_endpoint needs to be configured in a separate instance"):
        Istio('istio', {}, [{'istio_mesh_endpoint': 'http://mesh/metrics', 'istiod_endpoint': 'http://istiod/metrics'}])


def test_v1_metrics_combine_user_metrics_with_istiod_metrics():
    check = Istio('istio', {}, [{'istiod_endpoint': 'http://istiod/metrics', 'metrics': [{'foo': 'bar'}]}])
    assert check.instance['metrics'] == [{'foo': 'bar'}, ISTIOD_METRICS]


def test_v1_exclude_labels_combine_user_labels_with_blacklist():
    check = Istio('istio', {}, [{'istiod_endpoint': 'http://istiod/metrics', 'exclude_labels': ['custom']}])
    assert check.instance['exclude_labels'] == ['custom'] + BLACKLIST_LABELS


def test_v1_default_namespace_is_istio():
    check = Istio('istio', {}, [{'istiod_endpoint': 'http://istiod/metrics'}])
    assert check.instance['namespace'] == 'istio'


# --- legacy_1_4.py: LegacyIstioCheck_1_4 ---


def test_legacy_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at legacy_1_4.py:18 (DEFAULT_METRIC_LIMIT 0 -> 1).
    assert LegacyIstioCheck_1_4.DEFAULT_METRIC_LIMIT == 0


def test_legacy_mesh_instance_namespace_metrics_and_defaults():
    check = LegacyIstioCheck_1_4('istio', {}, [{'istio_mesh_endpoint': 'http://mesh/metrics'}])
    assert check.instance['namespace'] == 'istio.mesh'
    assert check.instance['metrics'] == [MESH_METRICS]
    assert check.instance['label_to_hostname'] == 'http://mesh/metrics'
    assert check.instance['send_monotonic_counter'] is False
    assert check.instance['health_service_check'] is False
    assert check.instance['send_monotonic_with_gauge'] is True


def test_legacy_mixer_instance_namespace_metrics_and_defaults():
    # Kills the 11 core/ReplaceBinaryOperator variants at legacy_1_4.py:139 and :147 (the two
    # `+` concatenations building the mixer namespace and metrics list): `str`/`list` only support
    # `+` between these operand types, so any other operator raises before this assertion runs.
    check = LegacyIstioCheck_1_4('istio', {}, [{'mixer_endpoint': 'http://mixer/metrics'}])
    assert check.instance['namespace'] == 'istio.mixer'
    assert check.instance['metrics'] == [MIXER_METRICS]
    assert check.instance['prometheus_url'] == 'http://mixer/metrics'
    # Kills the core/ReplaceTrueWithFalse mutants at legacy_1_4.py:149/:150 (the `False` defaults
    # for send_monotonic_counter/health_service_check).
    assert check.instance['send_monotonic_counter'] is False
    assert check.instance['health_service_check'] is False


def test_legacy_pilot_instance_namespace_and_metrics():
    # Kills the 11 core/ReplaceBinaryOperator variants at legacy_1_4.py:161 and :169.
    check = LegacyIstioCheck_1_4('istio', {}, [{'pilot_endpoint': 'http://pilot/metrics'}])
    assert check.instance['namespace'] == 'istio.pilot'
    assert check.instance['metrics'] == [PILOT_METRICS]
    assert check.instance['prometheus_url'] == 'http://pilot/metrics'


def test_legacy_galley_instance_namespace_metrics_and_ignore_metrics():
    # Kills the 11 core/ReplaceBinaryOperator variants at legacy_1_4.py:180 and :188.
    check = LegacyIstioCheck_1_4('istio', {}, [{'galley_endpoint': 'http://galley/metrics'}])
    assert check.instance['namespace'] == 'istio.galley'
    assert check.instance['metrics'] == [GALLEY_METRICS]
    assert check.instance['ignore_metrics'] == [
        'galley_mcp_source_message_size_bytes',
        'galley_mcp_source_request_acks_total',
    ]


def test_legacy_citadel_instance_namespace_and_metrics():
    # Kills the 11 core/ReplaceBinaryOperator variants at legacy_1_4.py:202 and :210.
    check = LegacyIstioCheck_1_4('istio', {}, [{'citadel_endpoint': 'http://citadel/metrics'}])
    assert check.instance['namespace'] == 'istio.citadel'
    assert check.instance['metrics'] == [CITADEL_METRICS]
    assert check.instance['prometheus_url'] == 'http://citadel/metrics'


def test_legacy_custom_namespace_override_applies_to_generated_instance():
    check = LegacyIstioCheck_1_4('istio', {}, [{'namespace': 'custom', 'mixer_endpoint': 'http://mixer/metrics'}])
    assert check.instance['namespace'] == 'custom.mixer'


def test_legacy_check_raises_when_no_endpoints_are_configured():
    # Kills the core/ReplaceFalseWithTrue mutant at legacy_1_4.py:35 (`processed = False`): without
    # the False initializer, the "at least one endpoint" guard would never fire.
    check = LegacyIstioCheck_1_4('istio', {}, [{}])
    with pytest.raises(CheckException, match="At least one of Mixer, Mesh, Pilot, Galley or Citadel"):
        check.check({})


def test_legacy_check_succeeds_with_mesh_endpoint_only():
    instance = {'istio_mesh_endpoint': 'http://mesh/metrics'}
    check = LegacyIstioCheck_1_4('istio', {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    check.process.assert_called_once()


def test_legacy_check_succeeds_with_mixer_endpoint_only():
    # Kills the core/ReplaceTrueWithFalse mutant at legacy_1_4.py:52 (`processed = True` after
    # processing mixer): without it, a mixer-only instance would wrongly raise CheckException.
    instance = {'mixer_endpoint': 'http://mixer/metrics'}
    check = LegacyIstioCheck_1_4('istio', {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    check.process.assert_called_once()


def test_legacy_check_succeeds_with_pilot_endpoint_only():
    # Kills the core/ReplaceTrueWithFalse mutant at legacy_1_4.py:61.
    instance = {'pilot_endpoint': 'http://pilot/metrics'}
    check = LegacyIstioCheck_1_4('istio', {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    check.process.assert_called_once()


def test_legacy_check_succeeds_with_galley_endpoint_only():
    # Kills the core/ReplaceTrueWithFalse mutant at legacy_1_4.py:70.
    instance = {'galley_endpoint': 'http://galley/metrics'}
    check = LegacyIstioCheck_1_4('istio', {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    check.process.assert_called_once()


def test_legacy_check_succeeds_with_citadel_endpoint_only():
    # Kills the core/ReplaceTrueWithFalse mutant at legacy_1_4.py:79.
    instance = {'citadel_endpoint': 'http://citadel/metrics'}
    check = LegacyIstioCheck_1_4('istio', {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    check.process.assert_called_once()


def test_legacy_check_processes_all_endpoint_types_when_all_are_configured():
    instance = {
        'istio_mesh_endpoint': 'http://mesh/metrics',
        'mixer_endpoint': 'http://mixer/metrics',
        'pilot_endpoint': 'http://pilot/metrics',
        'galley_endpoint': 'http://galley/metrics',
        'citadel_endpoint': 'http://citadel/metrics',
    }
    check = LegacyIstioCheck_1_4('istio', {}, [instance])
    check.process = mock.MagicMock()
    check.check(instance)
    assert check.process.call_count == 5
