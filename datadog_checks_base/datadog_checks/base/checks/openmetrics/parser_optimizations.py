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


def _is_char_escaped(text, pos):
    """Return True if the character at pos is preceded by an odd number of backslashes."""
    num_bslashes = 0
    while pos > num_bslashes and text[pos - 1 - num_bslashes] == '\\':
        num_bslashes += 1
    return num_bslashes % 2 == 1


def _next_unquoted_char(text, chs, startidx=0):
    """Find the next unquoted occurrence of any character in chs.

    Uses str.find() to jump to candidate characters, skipping over quoted regions.
    """
    if chs is None:
        chs = string.whitespace

    i = startidx
    n = len(text)

    while i < n:
        best = -1
        for ch in chs:
            p = text.find(ch, i)
            if p != -1 and (best == -1 or p < best):
                best = p

        # Find the next unescaped opening quote
        q = text.find('"', i)
        while q != -1 and _is_char_escaped(text, q):
            q = text.find('"', q + 1)

        # If no quote comes before the best candidate, return it directly
        if q == -1 or (best != -1 and best < q):
            return best

        # A quoted region starts before the candidate; skip over it
        close = text.find('"', q + 1)
        while close != -1 and _is_char_escaped(text, close):
            close = text.find('"', close + 1)

        if close == -1:
            return -1

        i = close + 1

    return -1


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
