# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from textwrap import dedent

from datadog_checks.dev.tooling.specs.docs import DocsSpec
from datadog_checks.dev.tooling.specs.docs.consumers import ReadmeConsumer

MOCK_RESPONSE = {'integration_id': 'foo'}


def get_doc(text, **kwargs):
    kwargs.setdefault('source', 'test')
    return DocsSpec(normalize_readme(text), **kwargs)


def get_readme_consumer(text, **kwargs):
    doc = get_doc(text, **kwargs)
    doc.load()
    return ReadmeConsumer(doc.data)


def normalize_readme(text):
    return dedent(text).lstrip()
