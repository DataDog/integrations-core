#  (C) Datadog, Inc. 2021-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)

from jsonpointer import resolve_pointer, set_pointer


class JSONDict(dict):
    """Subclass of dict which adds jsonpointer-like access methods"""

    def get_path(self, path):
        try:
            value = resolve_pointer(self, path)
        except Exception:
            value = None
        return value

    def set_path(self, path, value):
        # note we don't catch exceptions
        set_pointer(self, path, value)
