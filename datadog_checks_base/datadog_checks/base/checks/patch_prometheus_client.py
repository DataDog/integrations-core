# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# The goal is to improve performances or internal _parse_labels in prometheus_client
# No functional changes were made (just refactor the code)
#
# Original method as around 150% execution time than this one
# As long as this methods take around 50% of overall processing of open metrics that's a big gain
# Note: Compatible/Tested with prometheus-client 0.3.0
#
# Usage:
#
# replace:
#
# from prometheus_client.parser import text_fd_to_metric_families
#
# to:
#
# from .patch_prometheus_client import text_fd_to_metric_families

import re
from prometheus_client import parser

text_fd_to_metric_families = parser.text_fd_to_metric_families


ESCAPE_SEQUENCES = {
    '\\\\': '\\',
    '\\n': '\n',
    '\\"': '"',
}


def replace_escape_sequence(match):
    return ESCAPE_SEQUENCES[match.group(0)]


ESCAPING_RE = re.compile(r'\\[\\n"]')


def _replace_escaping(s):
    return ESCAPING_RE.sub(replace_escape_sequence, s)


def _is_character_escaped(s, charpos):
    num_bslashes = 0
    while (charpos > num_bslashes and
           s[charpos - 1 - num_bslashes] == '\\'):
        num_bslashes += 1
    return num_bslashes % 2 == 1


def _last_unescaped_quote(v):
    i = 0
    lv = len(v)
    while i < lv:
        i = v.index('"', i)
        if not _is_character_escaped(v, i):
            break
        i += 1
    return i


def _parse_labels(labels_string):
    # Return if we don't have valid labels
    try:
        value_start = labels_string.index("=")
    except ValueError:
        return {}
    try:
        # Copy original labels
        sub_labels = labels_string
        labels = {}
        # Process one label at a time
        escaping = "\\" in labels_string
        while True:
            # The label name is before the equal
            label_name = sub_labels[:value_start].strip()
            sub_labels = sub_labels[value_start + 1:].lstrip()
            # Find the first quote after the equal
            if escaping:
                quote_start = sub_labels.index('"') + 1
                # Find the last unescaped quote
                # The label value is inbetween the first and last quote
                quote_end = _last_unescaped_quote(sub_labels[quote_start:]) + 1
                labels[label_name] = _replace_escaping(sub_labels[quote_start:quote_end])
            else:
                quote_start = sub_labels.index('"') + 1
                quote_end = sub_labels.index('"', quote_start)
                labels[label_name] = sub_labels[quote_start:quote_end]

            # Remove the processed label from the sub-slice for next iteration
            sub_labels = sub_labels[quote_end + 1:]
            if not sub_labels:
                break
            sub_labels = sub_labels[sub_labels.find(",") + 1:]
            value_start = sub_labels.index("=")
        return labels

    except ValueError:
        raise ValueError("Invalid labels: %s" % labels_string)


# Replace current method with the fastest one
parser._parse_labels = _parse_labels
