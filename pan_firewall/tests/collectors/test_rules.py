# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.rules import collect_rule_hits, parse_rule_hits, rule_hit_cmd
from datadog_checks.pan_firewall.errors import PanosApiError, PanosAuthError

from ..helpers import load_op, make_ctx, series

pytestmark = pytest.mark.unit

RULE_HIT_CMD = rule_hit_cmd('vsys1')
HITS = {
    'trust-to-vpn': 476,
    'vpn-to-trust': 486,
    'trust-out': 1924,
    'deny-telnet': 0,
    'intrazone-default': 430,
    'interzone-default': 0,
}


def expected(rules=HITS, vsys='vsys1'):
    return {('security_rule.hits', (f'rule:{name}', f'vsys:{vsys}')): (HITS[name], 'monotonic_count') for name in rules}


@pytest.mark.parametrize(
    'patterns, rules',
    [
        pytest.param((), HITS, id='no-filter'),
        pytest.param(
            ('^deny-', 'default$'), ('deny-telnet', 'intrazone-default', 'interzone-default'), id='any-pattern'
        ),
    ],
)
def test_rule_hits_of_the_capture(patterns, rules):
    assert series(parse_rule_hits(load_op(RULE_HIT_CMD), 'vsys1', patterns, mock.Mock())) == expected(rules)


def test_rule_without_a_hit_count_is_skipped():
    root = load_op(RULE_HIT_CMD)
    rule = root.find("result/rule-hit-count/vsys/entry/rule-base/entry/rules/entry[@name='trust-out']")
    rule.remove(rule.find('hit-count'))

    samples = parse_rule_hits(root, 'vsys1', (), mock.Mock())

    assert series(samples) == expected([name for name in HITS if name != 'trust-out'])


def test_command_escapes_the_vsys_name():
    assert "<entry name='a&apos;b&amp;c&lt;'>" in rule_hit_cmd("a'b&c<")


def collect(vsys1, vsys2):
    """Run the collector on two vsys, each answering its parsed root or raising its exception."""
    answers = {rule_hit_cmd('vsys1'): vsys1, rule_hit_cmd('vsys2'): vsys2}

    def op(cmd):
        if isinstance(answer := answers[cmd], Exception):
            raise answer
        return answer

    ctx = make_ctx(state=FirewallState(vsys=['vsys1', 'vsys2']), config=mock.Mock(security_rule_filter=None))
    ctx.client.op.side_effect = op
    return collect_rule_hits(ctx)


def vsys2_answer():
    """The capture as vsys2 would answer it: the same rules under `<entry name="vsys2">`."""
    root = load_op(RULE_HIT_CMD)
    root.find('result/rule-hit-count/vsys/entry').set('name', 'vsys2')
    return root


def test_each_vsys_is_asked_and_tagged():
    samples = collect(load_op(RULE_HIT_CMD), vsys2_answer())

    assert series(samples) == expected() | expected(vsys='vsys2')


def test_a_refused_vsys_does_not_drop_the_others():
    samples = collect(load_op(RULE_HIT_CMD), PanosApiError('7', 'no'))

    assert series(samples) == expected()


@pytest.mark.parametrize(
    'vsys1, vsys2, error',
    [
        pytest.param(PanosApiError('7', 'no'), PanosApiError('7', 'no'), PanosApiError, id='every-vsys-refused'),
        pytest.param(load_op(RULE_HIT_CMD), PanosAuthError('403', 'no'), PanosAuthError, id='key-rejected'),
    ],
)
def test_the_collector_fails(vsys1, vsys2, error):
    with pytest.raises(error):
        collect(vsys1, vsys2)
