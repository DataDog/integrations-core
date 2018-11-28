# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


class NullContextManager(object):
    """
    A context manager that does nothing.
    """
    def __init__(self, thing=None):
        self.thing = thing

    def __enter__(self):
        return self.thing

    def __exit__(self, *args):
        pass
