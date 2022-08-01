# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from textwrap import dedent as _dedent


def dedent(text):
    return _dedent(text[1:])
