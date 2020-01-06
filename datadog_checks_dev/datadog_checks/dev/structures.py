# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import abc
import os
from shutil import rmtree
from tempfile import mkdtemp

import six

from ._env import e2e_active, get_env_vars, remove_env_vars, set_env_vars, tear_down_env
from .warn import warning


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


class TempDir(object):
    all_names = set()

    def __init__(self, name='default', base_directory=None):
        key = None
        directory = None

        if e2e_active():
            name = name.lower()

            if name in TempDir.all_names:
                raise Exception(
                    'Temporary directory name {} has already been used, choose a different one.'.format(name)
                )
            TempDir.all_names.add(name)

            key = 'temp_dir_{}'.format(name)
            env_vars = get_env_vars()

            if key in env_vars:
                directory = env_vars[key]
            else:
                directory = mkdtemp(dir=base_directory)
                set_env_vars({key: directory})

        self.name = name
        self.key = key
        self.directory = os.path.realpath(directory or mkdtemp(dir=base_directory))

    @classmethod
    def _cleanup(cls, directory):
        try:
            rmtree(directory)
        except Exception as e:
            warning('Error removing temporary directory `{}`: {}'.format(directory, e))

    def __enter__(self):
        return self.directory

    def __exit__(self, exc_type, exc_value, traceback):
        if e2e_active():
            if tear_down_env():
                TempDir.all_names.discard(self.name)
                remove_env_vars([self.key])
                self._cleanup(self.directory)
        else:
            self._cleanup(self.directory)
