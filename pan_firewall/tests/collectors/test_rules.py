# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.rules import collect_rule_hits, parse_rule_hits, rule_hit_cmd
from datadog_checks.pan_firewall.errors import PanosApiError, PanosAuthError

from ..helpers import load_op, make_ctx, series

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
    return load_op(RULE_HIT_CMD)


def expected(rules=None, vsys='vsys1'):
    return {
        ('security_rule.hits', (f'rule:{name}', f'vsys:{vsys}')): (hits, 'monotonic_count')
        for name, hits in HITS.items()
        if rules is None or name in rules
    }


def test_rule_hits_of_the_capture():
    samples = parse_rule_hits(load(), 'vsys1', (), mock.Mock())

    assert series(samples) == expected()


def test_security_rule_filter_keeps_a_rule_when_any_pattern_matches():
    samples = parse_rule_hits(load(), 'vsys1', ('^deny-', 'default$'), mock.Mock())

    assert series(samples) == expected({'deny-telnet', 'intrazone-default', 'interzone-default'})


def test_rule_without_a_hit_count_is_skipped():
    root = load()
    rule = root.find("result/rule-hit-count/vsys/entry/rule-base/entry/rules/entry[@name='trust-out']")
    rule.remove(rule.find('hit-count'))

    samples = parse_rule_hits(root, 'vsys1', (), mock.Mock())

    assert series(samples) == {k: v for k, v in expected().items() if k[1][0] != 'rule:trust-out'}


def test_command_escapes_the_vsys_name():
    assert "<entry name='a&apos;b&amp;c&lt;'>" in rule_hit_cmd("a'b&c<")


def vsys2_answer():
    """The capture as vsys2 would answer it: the same rules under `<entry name="vsys2">`."""
    root = load()
    root.find('result/rule-hit-count/vsys/entry').set('name', 'vsys2')
    return root


def test_collector_makes_one_call_per_vsys_and_tags_the_samples_with_it():
    answers = {rule_hit_cmd('vsys1'): load(), rule_hit_cmd('vsys2'): vsys2_answer()}
    ctx = make_ctx(answers, state=FirewallState(vsys=['vsys1', 'vsys2']), config=mock.Mock(security_rule_filter=None))

    samples = collect_rule_hits(ctx)

    assert [c.args[0] for c in ctx.client.op.call_args_list] == [rule_hit_cmd('vsys1'), rule_hit_cmd('vsys2')]
    assert series(samples) == {**expected(), **expected(vsys='vsys2')}


def _raise(error):
    raise error


def test_a_refused_vsys_does_not_drop_the_others():
    ctx = make_ctx(state=FirewallState(vsys=['vsys1', 'vsys2']), config=mock.Mock(security_rule_filter=None))
    good = load()
    ctx.client.op.side_effect = lambda cmd: good if cmd == rule_hit_cmd('vsys1') else _raise(PanosApiError('7', 'no'))

    samples = collect_rule_hits(ctx)

    assert series(samples) == expected()


def test_every_vsys_refused_fails_the_collector():
    ctx = make_ctx(state=FirewallState(vsys=['vsys1', 'vsys2']), config=mock.Mock(security_rule_filter=None))
    ctx.client.op.side_effect = PanosApiError('7', 'no')

    with pytest.raises(PanosApiError):
        collect_rule_hits(ctx)


def test_a_rejected_key_fails_the_collector_even_when_another_vsys_answers():
    ctx = make_ctx(state=FirewallState(vsys=['vsys1', 'vsys2']), config=mock.Mock(security_rule_filter=None))
    good = load()
    ctx.client.op.side_effect = (
        lambda cmd: good if cmd == rule_hit_cmd('vsys1') else _raise(PanosAuthError('403', 'no'))
    )

    with pytest.raises(PanosAuthError):
        collect_rule_hits(ctx)
