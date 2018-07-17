# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import abc
import os

import six


@six.add_metaclass(abc.ABCMeta)
class LazyFunction(object):
    """Abstract base class for lazy function calls."""

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        pass


class EnvVars(dict):
    def __init__(self, env_vars=None, ignore=None):
        super(EnvVars, self).__init__(os.environ)
        self.old_env = dict(self)

        if env_vars is not None:
            self.update(env_vars)

        if ignore is not None:
            for env_var in ignore:
                self.pop(env_var, None)

    def __enter__(self):
        os.environ.clear()
        os.environ.update(self)

    def __exit__(self, exc_type, exc_value, traceback):
        os.environ.clear()
        os.environ.update(self.old_env)
