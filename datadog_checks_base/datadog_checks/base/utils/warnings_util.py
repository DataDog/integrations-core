# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import warnings
from contextlib import contextmanager

from six import PY2


def _simplefilter_py2(action, category=Warning, lineno=0, append=0):
    """
    Add remove logic for py2 to avoid warnings.filters to growth
    indefinitely if simplefilter is called multiple times
    """
    item = (action, None, category, None, int(lineno))
    if not append:
        try:
            warnings.filters.remove(item)
        except ValueError:
            pass
    warnings.simplefilter(action, category=category, lineno=lineno, append=append)


if PY2:
    simplefilter = _simplefilter_py2
else:
    simplefilter = warnings.simplefilter


@contextmanager
def disable_warnings_ctx(action, disable=True):
    if disable:
        simplefilter('ignore', action)
        yield
        simplefilter('default', action)
    else:
        # do nothing
        yield
