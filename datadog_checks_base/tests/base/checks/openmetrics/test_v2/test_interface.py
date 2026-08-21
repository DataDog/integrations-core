# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.constants import ServiceCheck

from .utils import get_check


def test_default_config(aggregator, dd_run_check, mock_http_response):
    class Check(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = 'test'

        def get_default_config(self):
            return {'metrics': ['.+'], 'rename_labels': {'foo': 'bar'}}

    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="baz"} 6.396288e+06
        """
    )
    check = Check('test', {}, [{'openmetrics_endpoint': 'test'}])
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:baz']
    )

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    ('instance_renames', 'expected_tags'),
    [
        pytest.param({'qux': 'corge'}, ['endpoint:test', 'bar:baz', 'corge:quux'], id='disjoint_keys_merged'),
        pytest.param({'foo': 'corge'}, ['endpoint:test', 'corge:baz', 'qux:quux'], id='colliding_key_instance_wins'),
    ],
)
def test_default_rename_labels_merged_with_instance(
    aggregator, dd_run_check, mock_http_response, instance_renames, expected_tags
):
    """
    A `rename_labels` default is merged with the instance's `rename_labels`, entry by entry: disjoint
    keys union together, and on a key collision the instance's entry wins. The instance config is
    layered over the defaults in a `ChainMap`, which resolves keys shallowly, so without the merge an
    instance that sets `rename_labels` at all would shadow the class default wholesale and silently
    lose renames the check depends on.
    """

    class Check(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = 'test'

        def get_default_config(self):
            return {'metrics': ['.+'], 'rename_labels': {'foo': 'bar'}}

    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="baz",qux="quux"} 6.396288e+06
        """
    )
    check = Check('test', {}, [{'openmetrics_endpoint': 'test', 'rename_labels': instance_renames}])
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes',
        6396288,
        metric_type=aggregator.GAUGE,
        tags=expected_tags,
    )

    aggregator.assert_all_metrics_covered()


def test_default_config_mapping_not_shared_between_scrapers(aggregator, dd_run_check, mock_http_response):
    """
    A check with several scraper configs must not let one scraper's merged renames leak into
    another. The merge builds a fresh mapping per scraper instead of writing back into the dict
    `get_default_config` returns, so a second scraper that renames nothing keeps `qux` as `qux`
    even after a first scraper renamed it to `corge`.
    """
    default_renames = {'foo': 'bar'}

    class Check(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = 'test'

        def get_default_config(self):
            return {'metrics': ['.+'], 'rename_labels': default_renames}

    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{qux="quux"} 6.396288e+06
        """
    )
    check = Check('test', {}, [{'openmetrics_endpoint': 'test'}])
    check.scraper_configs = [
        {'openmetrics_endpoint': 'test1', 'rename_labels': {'qux': 'corge'}},
        {'openmetrics_endpoint': 'test2', 'rename_labels': {}},
    ]
    dd_run_check(check)

    # A leak would surface `qux` as `corge:quux` on the second scraper too.
    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test1', 'corge:quux']
    )
    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test2', 'qux:quux']
    )

    # The merge must not have mutated the dict `get_default_config` returned.
    assert default_renames == {'foo': 'bar'}


def test_default_config_only_rename_labels_is_merged():
    """
    Only `rename_labels` is merged with the check's declared default. Other mapping-valued options
    keep wholesale-replace semantics, so an instance can still fully override them -- e.g. disable a
    check's `share_labels` default by passing `{}`.
    """

    class Check(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = 'test'

        def get_default_config(self):
            return {'rename_labels': {'foo': 'bar'}, 'share_labels': {'cp_info': {'labels': ['version']}}}

    check = Check('test', {}, [{'openmetrics_endpoint': 'test'}])
    resolved = check.get_config_with_defaults(
        {'openmetrics_endpoint': 'test', 'rename_labels': {'qux': 'corge'}, 'share_labels': {}}
    )

    assert resolved['rename_labels'] == {'foo': 'bar', 'qux': 'corge'}
    assert resolved['share_labels'] == {}


def test_tag_by_endpoint(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="baz"} 6.396288e+06
        """
    )
    check = get_check({'metrics': ['.+'], 'tag_by_endpoint': False})
    dd_run_check(check)

    aggregator.assert_metric('test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['foo:baz'])


def test_service_check_dynamic_tags(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="baz"} 6.396288e+06
        # HELP state Node state
        # TYPE state gauge
        state{bar="baz"} 3
        """
    )
    check = get_check(
        {'metrics': ['.+', {'state': {'type': 'service_check', 'status_map': {'3': 'ok'}}}], 'tags': ['foo:bar']}
    )
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes',
        6396288,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'foo:bar', 'foo:baz'],
    )
    aggregator.assert_service_check('test.state', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])
    aggregator.assert_service_check('test.openmetrics.health', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_check_names) == 2

    aggregator.reset()
    check.set_dynamic_tags('baz:foo')
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes',
        6396288,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'foo:bar', 'foo:baz', 'baz:foo'],
    )
    aggregator.assert_service_check('test.state', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])
    aggregator.assert_service_check('test.openmetrics.health', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_check_names) == 2


def test_custom_transformer(aggregator, dd_run_check, mock_http_response):
    class Check(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = 'test'

        def __init__(self, name, init_config, instances):
            super().__init__(name, init_config, instances)
            self.check_initializations.append(self.configure_additional_transformers)

        def configure_transformer_watchdog_mega_miss(self):
            method = self.gauge

            def transform(metric, sample_data, runtime_data):
                for sample, tags, hostname in sample_data:
                    method('server.watchdog_mega_miss', sample.value, tags=tags, hostname=hostname)

            return transform

        def configure_additional_transformers(self):
            metric = r"^envoy_server_(.+)_watchdog_mega_miss$"
            self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
                metric, self.configure_transformer_watchdog_mega_miss(), pattern=True
            )

    mock_http_response(
        """
        # TYPE envoy_server_worker_0_watchdog_mega_miss counter
        envoy_server_worker_0_watchdog_mega_miss{} 1
        # TYPE envoy_server_worker_1_watchdog_mega_miss counter
        envoy_server_worker_1_watchdog_mega_miss{} 0
        """
    )
    check = Check('test', {}, [{'openmetrics_endpoint': 'test'}])
    dd_run_check(check)

    aggregator.assert_metric('test.server.watchdog_mega_miss', metric_type=aggregator.GAUGE, count=2)
