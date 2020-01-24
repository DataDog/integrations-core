# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import warnings

from ._env import e2e_active

_original_formatwarning = warnings.formatwarning


def warning(message):
    # We disable caching of this helper so it can be used multiple times.
    # https://github.com/python/cpython/blob/9a4758550d96030ee7e7f7c7c68b435db1a2a825/Lib/warnings.py#L362
    with warnings.catch_warnings():
        warnings.warn(message, stacklevel=2)


def _formatwarning(message, category, filename, lineno, line=None):
    # Shorten output for occurrences during E2E to just what is necessary for a nice display.
    if e2e_active():
        return '{}\n'.format(message)

    return _original_formatwarning(message, category, filename, lineno, line=line)


# We can't override `showwarning` as usual because pytest already overrides that for logs.
# https://github.com/pytest-dev/pytest/blob/b76104e722f41ce367765cd988ee8314d45b20b5/src/_pytest/warnings.py#L75
warnings.formatwarning = _formatwarning
