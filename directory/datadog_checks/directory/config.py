# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from os.path import abspath
from re import compile as re_compile

from datadog_checks.base import ConfigurationError, is_affirmative

MAX_FILEGAUGE_COUNT = 20


class DirectoryConfig(object):
    def __init__(self, instance):
        if 'directory' not in instance:
            raise ConfigurationError('DirectoryCheck: missing `directory` in config')
        directory = instance['directory']

        self.abs_directory = abspath(directory)
        self.name = instance.get('name', directory)
        self.pattern = instance.get('pattern')
        exclude_dirs = instance.get('exclude_dirs', [])
        self.exclude_dirs_pattern = re_compile('|'.join(exclude_dirs)) if exclude_dirs else None
        self.dirs_patterns_full = is_affirmative(instance.get('dirs_patterns_full', False))
        self.recursive = is_affirmative(instance.get('recursive', False))
        self.dirtagname = instance.get('dirtagname', 'name')
        self.filetagname = instance.get('filetagname', 'filename')
        self.filegauges = is_affirmative(instance.get('filegauges', False))
        self.countonly = is_affirmative(instance.get('countonly', False))
        self.ignore_missing = is_affirmative(instance.get('ignore_missing', False))
        self.follow_symlinks = is_affirmative(instance.get('follow_symlinks', True))
        self.stat_follow_symlinks = is_affirmative(instance.get('stat_follow_symlinks', True))
        self.submit_histograms = is_affirmative(instance.get('submit_histograms', True))
        self.tags = instance.get('tags', [])
        self.max_filegauge_count = instance.get('max_filegauge_count', MAX_FILEGAUGE_COUNT)
