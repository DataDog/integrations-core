# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.rules import collect_rule_hits, parse_rule_hits, rule_hit_cmd
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_TAGS
from ..fixture_map import OP_FIXTURES, op_fixture
from ..helpers import new_check

RULE_HIT_CMD = rule_hit_cmd('vsys1')
HITS = {
    'trust-to-vpn': 476,
    'vpn-to-trust': 486,
    'trust-out': 1924,
    'deny-telnet': 0,
    'intrazone-default': 430,
    'interzone-default': 0,
}


def load():
    return parse_response(op_fixture(RULE_HIT_CMD).read_bytes())


def expected(rules=None, vsys='vsys1'):
    return {
        ('security_rule.hits', (f'rule:{name}', f'vsys:{vsys}')): (hits, 'monotonic_count')
        for name, hits in HITS.items()
        if rules is None or name in rules
    }


def series(samples):
    result = {(s.name, s.tags): (s.value, s.kind) for s in samples}
    assert len(result) == len(samples)
    return result


def test_rule_hits_of_the_capture():
    samples = parse_rule_hits(load(), 'vsys1', (), mock.Mock())

    assert series(samples) == expected()


@pytest.mark.parametrize(
    'patterns, kept',
    [
        pytest.param((), set(HITS), id='empty-keeps-all'),
        pytest.param(('^trust-',), {'trust-to-vpn', 'trust-out'}, id='one-pattern'),
        pytest.param(('^deny-', 'default$'), {'deny-telnet', 'intrazone-default', 'interzone-default'}, id='any-match'),
        pytest.param(('^nothing$',), set(), id='no-match'),
    ],
)
def test_security_rule_filter_keeps_a_rule_when_any_pattern_matches(patterns, kept):
    samples = parse_rule_hits(load(), 'vsys1', patterns, mock.Mock())

    assert series(samples) == expected(kept)


def test_unknown_shape_warns_and_sends_nothing():
    log = mock.Mock()

    samples = parse_rule_hits(parse_response(b'<response status="success"/>'), 'vsys1', (), log)

    assert samples == []
    log.warning.assert_called_once()


def test_rule_without_a_hit_count_is_skipped():
    root = load()
    rule = root.find("result/rule-hit-count/vsys/entry/rule-base/entry/rules/entry[@name='trust-out']")
    rule.remove(rule.find('hit-count'))

    samples = parse_rule_hits(root, 'vsys1', (), mock.Mock())

    assert series(samples) == {k: v for k, v in expected().items() if k[1][0] != 'rule:trust-out'}


def test_command_matches_the_captured_one_and_escapes_the_vsys_name():
    assert RULE_HIT_CMD in OP_FIXTURES
    assert "<entry name='a&apos;b&amp;c&lt;'>" in rule_hit_cmd("a'b&c<")


def make_context(vsys, patterns=None):
    ctx = CollectContext(
        client=mock.Mock(),
        identity=mock.Mock(),
        state=FirewallState(vsys=vsys),
        config=mock.Mock(security_rule_filter=patterns),
        log=mock.Mock(),
    )
    ctx.client.op.side_effect = lambda cmd: load()
    return ctx


def test_collector_makes_one_call_per_vsys_and_tags_the_samples_with_it():
    ctx = make_context(['vsys1', 'vsys2'])

    samples = collect_rule_hits(ctx)

    assert [c.args[0] for c in ctx.client.op.call_args_list] == [rule_hit_cmd('vsys1'), rule_hit_cmd('vsys2')]
    assert series(samples) == {**expected(), **expected(vsys='vsys2')}


def test_collector_applies_the_configured_filter():
    ctx = make_context(['vsys1'], ('^trust-out$',))

    assert series(collect_rule_hits(ctx)) == expected({'trust-out'})


def test_rule_hits_are_registered_and_submit_through_the_check(real_collectors, dd_run_check, aggregator):
    assert 'rule_hits' in COLLECT_FUNCTIONS

    dd_run_check(new_check())

    for name, hits in HITS.items():
        aggregator.assert_metric(
            'pan_firewall.security_rule.hits',
            hits,
            tags=sorted([*FW_A_TAGS, f'rule:{name}', 'vsys:vsys1']),
            metric_type=aggregator.MONOTONIC_COUNT,
        )
    assert len(aggregator.metrics('pan_firewall.security_rule.hits')) == 6
