# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from fnmatch import fnmatch
from os.path import exists, join, relpath
from time import time
from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.directory.config import DirectoryConfig

from .traverse import walk

SERVICE_DIRECTORY_EXISTS = 'system.disk.directory.exists'


class DirectoryCheck(AgentCheck):
    """This check is for monitoring and reporting metrics on the files for a provided directory.

    WARNING: the user/group that the agent runs as must have access to stat the files in the desired directory

    Config options:
        `directory` - string, the directory to gather stats for. required
        `name` - string, the name to use when tagging the metrics. defaults to the `directory`
        `dirtagname` - string, the name of the tag used for the directory. defaults to `name`
        `filetagname` - string, the name of the tag used for each file. defaults to `filename`
        `filegauges` - boolean, when true stats will be an individual gauge per file (max. 20 files!)
                       and not a histogram of the whole directory. default False
        `pattern` - string, the `fnmatch` pattern to use when reading the `directory`'s files. default `*`
        `recursive` - boolean, when true the stats will recurse into directories. default False
        `countonly` - boolean, when true the stats will only count the number of files matching the pattern.
                      Useful for very large directories. default False
        `ignore_missing` - boolean, when true do not raise an exception on missing/inaccessible directories.
                           default False
    """

    SOURCE_TYPE_NAME = 'system'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(DirectoryCheck, self).__init__(*args, **kwargs)

        self.config = DirectoryConfig(self.instance)

    def check(self, _):
        service_check_tags = ['dir_name:{}'.format(self.config.name)]
        service_check_tags.extend(self.config.tags)
        if not exists(self.config.abs_directory):
            msg = (
                "Either directory '{}' doesn't exist or the Agent doesn't "
                "have permissions to access it, skipping.".format(self.config.abs_directory)
            )
            # report missing directory
            self.service_check(name=SERVICE_DIRECTORY_EXISTS, status=self.WARNING, tags=service_check_tags, message=msg)

            # raise exception if `ignore_missing` is False
            if not self.config.ignore_missing:
                raise CheckException(msg)

            self.log.warning(msg)

            # return gracefully, nothing to look for
            return

        self.service_check(name=SERVICE_DIRECTORY_EXISTS, tags=service_check_tags, status=self.OK)
        self._get_stats()

    def _get_stats(self):
        dirtags = ['{}:{}'.format(self.config.dirtagname, self.config.name)]
        dirtags.extend(self.config.tags)
        directory_bytes = 0
        directory_files = 0
        max_filegauge_balance = self.config.max_filegauge_count

        # If we do not want to recursively search sub-directories only get the root.
        walker = walk(self.config.abs_directory, self.config.follow_symlinks)
        if not self.config.recursive:
            # Only visit the first directory.
            walker = [next(walker)]

        # Avoid repeated global lookups.
        get_length = len

        for root, dirs, files in walker:
            matched_files = []
            adjust_max_filegauge = False

            if self.config.exclude_dirs_pattern is not None:
                if self.config.dirs_patterns_full:
                    dirs[:] = [d for d in dirs if not self.config.exclude_dirs_pattern.search(d.path)]
                else:
                    dirs[:] = [d for d in dirs if not self.config.exclude_dirs_pattern.search(d.name)]

            if self.config.pattern is not None:
                # Check if the path of the file relative to the directory
                # matches the pattern. Also check if the absolute path of the
                # filename matches the pattern, for compatibility with previous
                # agent versions.
                for file_entry in files:
                    filename = join(root, file_entry.name)
                    if fnmatch(filename, self.config.pattern) or fnmatch(
                        relpath(filename, self.config.abs_directory), self.config.pattern
                    ):
                        matched_files.append(file_entry)
            else:
                matched_files = list(files)

            matched_files_length = get_length(matched_files)
            directory_files += matched_files_length

            # We're just looking to count the files.
            if self.config.countonly:
                continue

            for file_entry in matched_files:
                try:
                    file_stat = file_entry.stat(follow_symlinks=self.config.stat_follow_symlinks)

                except OSError as ose:
                    self.warning('DirectoryCheck: could not stat file %s - %s', join(root, file_entry.name), ose)
                else:
                    # file specific metrics
                    directory_bytes += file_stat.st_size
                    if self.config.filegauges and matched_files_length <= max_filegauge_balance:
                        filetags = ['{}:{}'.format(self.config.filetagname, join(root, file_entry.name))]
                        filetags.extend(dirtags)
                        self.gauge('system.disk.directory.file.bytes', file_stat.st_size, tags=filetags)
                        self.gauge(
                            'system.disk.directory.file.modified_sec_ago', time() - file_stat.st_mtime, tags=filetags
                        )
                        self.gauge(
                            'system.disk.directory.file.created_sec_ago', time() - file_stat.st_ctime, tags=filetags
                        )
                        adjust_max_filegauge = True
                    else:
                        self.histogram('system.disk.directory.file.bytes', file_stat.st_size, tags=dirtags)
                        self.histogram(
                            'system.disk.directory.file.modified_sec_ago', time() - file_stat.st_mtime, tags=dirtags
                        )
                        self.histogram(
                            'system.disk.directory.file.created_sec_ago', time() - file_stat.st_ctime, tags=dirtags
                        )
            if adjust_max_filegauge:
                max_filegauge_balance -= matched_files_length

        # number of files
        self.gauge('system.disk.directory.files', directory_files, tags=dirtags)

        # total file size
        if not self.config.countonly:
            self.gauge('system.disk.directory.bytes', directory_bytes, tags=dirtags)
