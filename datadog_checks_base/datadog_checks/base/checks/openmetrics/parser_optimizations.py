# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Optimized replacements for prometheus_client parser hot-path functions.

prometheus_client v0.22.0 rewrote label/sample parsing to support UTF-8 metric
names, replacing direct str.index()/str.rindex() calls with a character-by-character
scanning function (_next_unquoted_char). This caused a ~3-5x performance regression
(see https://github.com/prometheus/client_python/issues/1114).

This module restores the pre-v0.22.0 parsing approach by replacing _parse_sample
and _parse_labels with their v0.21.1 implementations that use C-level str.index()
and str.rindex() for fast delimiter lookup. For the OpenMetrics parser (which has
no v0.21.1 equivalent), _next_unquoted_char is replaced with a str.find()-based
version that avoids character-by-character iteration.

The original v0.21.1 source:
https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/parser.py
"""

import string

import prometheus_client.parser as _prom_parser
from prometheus_client.samples import Sample


# Copied from prometheus_client v0.21.1:
# https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/parser.py#L56-L97
def _parse_labels(labels_string):
    labels = {}
    # Return if we don't have valid labels
    if "=" not in labels_string:
        return labels

    escaping = False
    if "\\" in labels_string:
        escaping = True

    # Copy original labels
    sub_labels = labels_string
    try:
        # Process one label at a time
        while sub_labels:
            # The label name is before the equal
            value_start = sub_labels.index("=")
            label_name = sub_labels[:value_start]
            sub_labels = sub_labels[value_start + 1 :].lstrip()
            # Find the first quote after the equal
            quote_start = sub_labels.index('"') + 1
            value_substr = sub_labels[quote_start:]

            # Find the last unescaped quote
            i = 0
            while i < len(value_substr):
                i = value_substr.index('"', i)
                if not _prom_parser._is_character_escaped(value_substr, i):
                    break
                i += 1

            # The label value is between the first and last quote
            quote_end = i + 1
            label_value = sub_labels[quote_start:quote_end]
            # Replace escaping if needed
            if escaping:
                label_value = _prom_parser._replace_escaping(label_value)
            labels[label_name.strip()] = label_value

            # Remove the processed label from the sub-slice for next iteration
            sub_labels = sub_labels[quote_end + 1 :]
            next_comma = sub_labels.find(",") + 1
            sub_labels = sub_labels[next_comma:].lstrip()

        return labels

    except ValueError:
        raise ValueError("Invalid labels: %s" % labels_string)


# Copied from prometheus_client v0.21.1:
# https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/parser.py#L110-L129
def _parse_sample(text):
    # Detect the labels in the text
    try:
        label_start, label_end = text.index("{"), text.rindex("}")
        # The name is before the labels
        name = text[:label_start].strip()
        # We ignore the starting curly brace
        label = text[label_start + 1 : label_end]
        # The value is after the label end (ignoring curly brace)
        value, timestamp = _prom_parser._parse_value_and_timestamp(text[label_end + 1 :])
        return Sample(name, _parse_labels(label), value, timestamp)

    # We don't have labels
    except ValueError:
        # Detect what separator is used
        separator = " "
        if separator not in text:
            separator = "\t"
        name_end = text.index(separator)
        name = text[:name_end]
        # The value is after the name
        value, timestamp = _prom_parser._parse_value_and_timestamp(text[name_end:])
        return Sample(name, {}, value, timestamp)


def _next_unquoted_char(text, chs, startidx=0):
    """str.find()-based replacement for the character-by-character _next_unquoted_char.

    Used for the OpenMetrics parser path which has no v0.21.1 equivalent to copy.
    """
    if chs is None:
        chs = string.whitespace

    best = -1
    for ch in chs:
        p = text.find(ch, startidx)
        if p != -1 and (best == -1 or p < best):
            best = p
    return best


def apply():
    """Monkey-patch prometheus_client parsers with optimized hot-path functions."""
    if getattr(_prom_parser, '_dd_optimized', False):
        return

    # Prometheus text format: replace _parse_sample with v0.21.1 implementation
    _prom_parser._parse_sample = _parse_sample
    _prom_parser._dd_optimized = True

    # OpenMetrics format: replace _next_unquoted_char with str.find() version.
    # The OpenMetrics parser imports _next_unquoted_char, parse_labels, and
    # _split_quoted from prometheus_client.parser via `from ..parser import`,
    # so we must patch both modules' bindings.
    _prom_parser._next_unquoted_char = _next_unquoted_char
    try:
        import prometheus_client.openmetrics.parser as _om_parser

        _om_parser._next_unquoted_char = _next_unquoted_char
    except (ImportError, AttributeError):
        pass


apply()
