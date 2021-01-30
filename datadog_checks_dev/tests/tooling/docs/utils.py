# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from textwrap import dedent

from datadog_checks.dev.tooling.specs.docs import DocsSpec


def get_doc(text, **kwargs):
    kwargs.setdefault('source', 'test')
    return DocsSpec(normalize_yaml(text), **kwargs)


def normalize_yaml(text):
    return dedent(text).lstrip()
