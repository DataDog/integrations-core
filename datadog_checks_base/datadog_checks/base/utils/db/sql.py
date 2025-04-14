# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import mmh3

from datadog_checks.base import ensure_bytes
from datadog_checks.base.utils.serialization import json, sort_keys_kwargs

# Unicode character "Arabic Decimal Separator" (U+066B) is a character which looks like an ascii
# comma, but is not treated like a comma when parsing metrics tags. This is used to replace
# commas so that tags which have commas in them (such as SQL queries) properly display.
ARABIC_DECIMAL_SEPARATOR = '，'


def compute_sql_signature(normalized_query):
    """
    Given an already obfuscated & normalized SQL query, generate its 64-bit hex signature.
    """
    if not normalized_query:
        return None
    # Note: please be cautious when changing this function as some features rely on this
    # hash matching the APM resource hash generated on our backend.
    return format(mmh3.hash64(ensure_bytes(normalized_query), signed=False)[0], 'x')


def normalize_query_tag(query):
    """
    Normalize the SQL query value to be used as a tag on metrics.

    HACK: This function substitutes ascii commas in the query with a special unicode
    character which is not normalized into a comma by metrics backend. This is a temporary
    hack to work around the bugs in the "Arbitrary Tag Values" feature on the backend
    which allows for any unicode string characters to be used as tag values without being
    escaped. Ascii commas in tag values are not currently supported in the query language,
    so this replacement is a workaround to display commas in tags but still allow metric
    queries to work.

    For Datadog employees, more background on "Arbitrary Tag Values":
    https://docs.google.com/document/d/1LQWw6ZiQZW18lknsBAZFMrba8BQ5yOmaWoEC7J1nLxU
    """
    query = query.replace(', ', '{} '.format(ARABIC_DECIMAL_SEPARATOR)).replace(',', ARABIC_DECIMAL_SEPARATOR)
    return query


def compute_exec_plan_signature(normalized_json_plan):
    """
    Given an already normalized json string query execution plan, generate its 64-bit hex signature.
    TODO: try to push this logic into the agent go code to avoid the two extra json serialization steps here
    """
    if not normalized_json_plan:
        return None
    with_sorted_keys = json.dumps(json.loads(normalized_json_plan), **sort_keys_kwargs)
    return format(mmh3.hash64(with_sorted_keys, signed=False)[0], 'x')
