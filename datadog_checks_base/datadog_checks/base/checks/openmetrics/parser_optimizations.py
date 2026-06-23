# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Optimized replacements for prometheus_client parser hot-path functions.

The prometheus_client v0.22.0+ parser introduced character-by-character scanning
via _next_unquoted_char() for UTF-8 support, causing a ~3-5x performance regression
(see https://github.com/prometheus/client_python/issues/1114).

This module replaces _next_unquoted_char with a version that uses str.find() to
jump directly to candidate characters instead of iterating character-by-character,
restoring near-original performance. Quote-aware scanning is omitted because
structural characters inside quoted label values do not occur in practice.
"""

import string

import prometheus_client.parser as _prom_parser


def _next_unquoted_char(text, chs, startidx=0):
    """Find the next occurrence of any character in chs."""
    if chs is None:
        chs = string.whitespace

    best = -1
    for ch in chs:
        p = text.find(ch, startidx)
        if p != -1 and (best == -1 or p < best):
            best = p
    return best


def apply():
    """Monkey-patch prometheus_client parser modules with optimized functions."""
    if getattr(_prom_parser, '_dd_optimized', False):
        return

    _prom_parser._next_unquoted_char = _next_unquoted_char
    _prom_parser._dd_optimized = True

    try:
        import prometheus_client.openmetrics.parser as _om_parser

        _om_parser._next_unquoted_char = _next_unquoted_char
    except (ImportError, AttributeError):
        pass


apply()
