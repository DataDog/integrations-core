# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Optimized replacements for prometheus_client parser hot-path functions.

prometheus_client v0.22.0 rewrote label/sample parsing to support UTF-8 metric
names, replacing direct str.index()/str.rindex() calls with a character-by-character
scanning function (_next_unquoted_char). This caused a ~3-5x performance regression
(see https://github.com/prometheus/client_python/issues/1114).

This module restores the pre-v0.22.0 parsing approach by replacing _parse_sample
in both the Prometheus text format and OpenMetrics parsers with their v0.21.1
implementations that use C-level str.index()/str.rindex() for fast delimiter lookup.

The original v0.21.1 sources:
https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/parser.py
https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/openmetrics/parser.py
"""

import prometheus_client.parser as _prom_parser
from prometheus_client.samples import Sample
from prometheus_client.validation import METRIC_LABEL_NAME_RE

try:
    import prometheus_client.openmetrics.parser as _om_parser
except ImportError:
    _om_parser = None


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


# Copied from prometheus_client v0.21.1:
# https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/openmetrics/parser.py#L116-L181
def _om_parse_labels_with_state_machine(text):
    # The { has already been parsed.
    state = 'startoflabelname'
    labelname = []
    labelvalue = []
    labels = {}
    labels_len = 0

    for char in text:
        if state == 'startoflabelname':
            if char == '}':
                state = 'endoflabels'
            else:
                state = 'labelname'
                labelname.append(char)
        elif state == 'labelname':
            if char == '=':
                state = 'labelvaluequote'
            else:
                labelname.append(char)
        elif state == 'labelvaluequote':
            if char == '"':
                state = 'labelvalue'
            else:
                raise ValueError("Invalid line: " + text)
        elif state == 'labelvalue':
            if char == '\\':
                state = 'labelvalueslash'
            elif char == '"':
                ln = ''.join(labelname)
                if not METRIC_LABEL_NAME_RE.match(ln):
                    raise ValueError("Invalid line, bad label name: " + text)
                if ln in labels:
                    raise ValueError("Invalid line, duplicate label name: " + text)
                labels[ln] = ''.join(labelvalue)
                labelname = []
                labelvalue = []
                state = 'endoflabelvalue'
            else:
                labelvalue.append(char)
        elif state == 'endoflabelvalue':
            if char == ',':
                state = 'labelname'
            elif char == '}':
                state = 'endoflabels'
            else:
                raise ValueError("Invalid line: " + text)
        elif state == 'labelvalueslash':
            state = 'labelvalue'
            if char == '\\':
                labelvalue.append('\\')
            elif char == 'n':
                labelvalue.append('\n')
            elif char == '"':
                labelvalue.append('"')
            else:
                labelvalue.append('\\' + char)
        elif state == 'endoflabels':
            if char == ' ':
                break
            else:
                raise ValueError("Invalid line: " + text)
        labels_len += 1
    return labels, labels_len


# Copied from prometheus_client v0.21.1:
# https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/openmetrics/parser.py#L182-L248
def _om_parse_labels(text):
    labels = {}

    # Raise error if we don't have valid labels
    if text and "=" not in text:
        raise ValueError

    # Copy original labels
    sub_labels = text
    try:
        # Process one label at a time
        while sub_labels:
            # The label name is before the equal
            value_start = sub_labels.index("=")
            label_name = sub_labels[:value_start]
            sub_labels = sub_labels[value_start + 1 :]

            # Check for missing quotes
            if not sub_labels or sub_labels[0] != '"':
                raise ValueError

            # The first quote is guaranteed to be after the equal
            value_substr = sub_labels[1:]

            # Check for extra commas
            if not label_name or label_name[0] == ',':
                raise ValueError
            if not value_substr or value_substr[-1] == ',':
                raise ValueError

            # Find the last unescaped quote
            i = 0
            while i < len(value_substr):
                i = value_substr.index('"', i)
                if not _om_parser._is_character_escaped(value_substr[:i], i):
                    break
                i += 1

            # The label value is between the first and last quote
            quote_end = i + 1
            label_value = sub_labels[1:quote_end]
            # Replace escaping if needed
            if "\\" in label_value:
                label_value = _om_parser._replace_escaping(label_value)
            if not METRIC_LABEL_NAME_RE.match(label_name):
                raise ValueError("invalid line, bad label name: " + text)
            if label_name in labels:
                raise ValueError("invalid line, duplicate label name: " + text)
            labels[label_name] = label_value

            # Remove the processed label from the sub-slice for next iteration
            sub_labels = sub_labels[quote_end + 1 :]
            if sub_labels.startswith(","):
                next_comma = 1
            else:
                next_comma = 0
            sub_labels = sub_labels[next_comma:]

            # Check for missing commas
            if sub_labels and next_comma == 0:
                raise ValueError

        return labels

    except ValueError:
        raise ValueError("Invalid labels: " + text)


# Copied from prometheus_client v0.21.1:
# https://github.com/prometheus/client_python/blob/v0.21.1/prometheus_client/openmetrics/parser.py#L250-L279
def _om_parse_sample(text):
    separator = " # "
    # Detect the labels in the text
    label_start = text.find("{")
    if label_start == -1 or separator in text[:label_start]:
        # We don't have labels, but there could be an exemplar.
        name_end = text.index(" ")
        name = text[:name_end]
        # Parse the remaining text after the name
        remaining_text = text[name_end + 1 :]
        value, timestamp, exemplar = _om_parser._parse_remaining_text(remaining_text)
        return Sample(name, {}, value, timestamp, exemplar)
    # The name is before the labels
    name = text[:label_start]
    if separator not in text:
        # Line doesn't contain an exemplar
        # We can use `rindex` to find `label_end`
        label_end = text.rindex("}")
        label = text[label_start + 1 : label_end]
        labels = _om_parse_labels(label)
    else:
        # Line potentially contains an exemplar
        # Fallback to parsing labels with a state machine
        labels, labels_len = _om_parse_labels_with_state_machine(text[label_start + 1 :])
        label_end = labels_len + len(name)
    # Parsing labels succeeded, continue parsing the remaining text
    remaining_text = text[label_end + 2 :]
    value, timestamp, exemplar = _om_parser._parse_remaining_text(remaining_text)
    return Sample(name, labels, value, timestamp, exemplar)


def apply():
    """Monkey-patch prometheus_client parsers with optimized hot-path functions."""
    if getattr(_prom_parser, '_dd_optimized', False):
        return

    # Prometheus text format: replace _parse_sample with v0.21.1 implementation
    _prom_parser._parse_sample = _parse_sample
    _prom_parser._dd_optimized = True

    # OpenMetrics format: replace _parse_sample with v0.21.1 implementation
    if _om_parser is not None:
        _om_parser._parse_sample = _om_parse_sample


apply()
