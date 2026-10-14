# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Security rule hit counts (`show rule-hit-count`), one call per vsys."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from functools import cache
from xml.etree.ElementTree import Element
from xml.sax.saxutils import escape

from datadog_checks.pan_firewall.xml_utils import num

from . import CollectContext, Sample, register


@cache
def _compile_filter(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    """Config validation has already rejected a pattern that does not compile."""
    return tuple(re.compile(p) for p in patterns)


def rule_hit_cmd(vsys: str) -> str:
    """The vsys name is escaped for the single-quoted XML attribute."""
    name = escape(vsys, {"'": '&apos;'})
    return (
        f"<show><rule-hit-count><vsys><vsys-name><entry name='{name}'><rule-base><entry name='security'>"
        '<rules><all/></rules></entry></rule-base></entry></vsys-name></vsys></rule-hit-count></show>'
    )


def parse_rule_hits(root: Element, vsys: str, patterns: Sequence[str], warn: Callable[..., None]) -> list[Sample]:
    rules = root.find('result/rule-hit-count/vsys/entry/rule-base/entry/rules')
    if rules is None:
        warn('Unknown shape of `show rule-hit-count` for %s: no rules element, sending no rule metrics', vsys)
        return []

    compiled = _compile_filter(tuple(patterns))
    samples: list[Sample] = []
    for rule in rules.iterfind('entry'):
        name = rule.get('name')
        hits = num(rule, 'hit-count')
        if not name or hits is None or (compiled and not any(p.search(name) for p in compiled)):
            continue
        samples.append(Sample('security_rule.hits', hits, (f'rule:{name}', f'vsys:{vsys}'), 'monotonic_count'))
    return samples


@register('rule_hits')
def collect_rule_hits(ctx: CollectContext) -> list[Sample]:
    patterns = ctx.config.security_rule_filter or ()
    samples: list[Sample] = []
    for vsys in ctx.state.vsys:
        samples.extend(parse_rule_hits(ctx.client.op(rule_hit_cmd(vsys)), vsys, patterns, ctx.warning))
    return samples
