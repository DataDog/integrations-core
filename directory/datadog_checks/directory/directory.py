# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
from fnmatch import fnmatch
from os.path import exists, join, realpath, relpath
from time import time
from typing import Any  # noqa: F401

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

        self._config = DirectoryConfig(self.instance)

    def check(self, _):
        service_check_tags = ['dir_name:{}'.format(self._config.name)]
        service_check_tags.extend(self._config.tags)
        if not exists(self._config.abs_directory):
            msg = (
                "Either directory '{}' doesn't exist or the Agent doesn't "
                "have permissions to access it, skipping.".format(self._config.abs_directory)
            )
            # report missing directory
            self.service_check(name=SERVICE_DIRECTORY_EXISTS, status=self.WARNING, tags=service_check_tags, message=msg)

            # raise exception if `ignore_missing` is False
            if not self._config.ignore_missing:
                raise CheckException(msg)

            self.log.warning(msg)

            # return gracefully, nothing to look for
            return

        self.service_check(name=SERVICE_DIRECTORY_EXISTS, tags=service_check_tags, status=self.OK)
        self._get_stats()

    def _get_stats(self):
        dirtags = ['{}:{}'.format(self._config.dirtagname, self._config.name)]
        dirtags.extend(self._config.tags)
        directory_bytes = 0
        directory_files = 0
        directory_folders = 0
        max_filegauge_balance = self._config.max_filegauge_count
        submit_histograms = self._config.submit_histograms

        # Avoid repeated global lookups.
        get_length = len

        # Avoid duplicate files for directory bytes
        seen_files = defaultdict(lambda: defaultdict(int))

        for root, dirs, files in self._walk():
            matched_files = []
            adjust_max_filegauge = False

            if self._config.exclude_dirs_pattern is not None:
                if self._config.dirs_patterns_full:
                    dirs[:] = [d for d in dirs if not self._config.exclude_dirs_pattern.search(d.path)]
                else:
                    dirs[:] = [d for d in dirs if not self._config.exclude_dirs_pattern.search(d.name)]
                self.log.debug('Directories: %s', str(dirs))
            directory_folders += get_length(dirs)

            if self._config.pattern is not None:
                # Check if the path of the file relative to the directory
                # matches the pattern. Also check if the absolute path of the
                # filename matches the pattern, for compatibility with previous
                # agent versions.
                for file_entry in files:
                    filename = join(root, file_entry.name)
                    if fnmatch(filename, self._config.pattern) or fnmatch(
                        relpath(filename, self._config.abs_directory), self._config.pattern
                    ):
                        matched_files.append(file_entry)
            else:
                matched_files = list(files)

            matched_files_length = get_length(matched_files)
            directory_files += matched_files_length

            # We're just looking to count the files.
            if self._config.countonly:
                continue

            for file_entry in matched_files:
                try:
                    self.log.debug('File entries in matched files: %s', str(file_entry))
                    file_stat = file_entry.stat(follow_symlinks=self._config.stat_follow_symlinks)
                    real_path = realpath(file_entry.path)
                except OSError as ose:
                    self.log.debug(
                        'DirectoryCheck: could not stat file %s, skipping it - %s', join(root, file_entry.name), ose
                    )
                else:
                    # Directory bytes metric
                    if real_path not in seen_files.keys():
                        directory_bytes += file_stat.st_size
                        if self._config.stat_follow_symlinks:
                            seen_files[real_path].setdefault('lnks', []).append(file_entry.path)
                            seen_files[real_path]['size'] += file_stat.st_size
                        else:
                            seen_files[file_entry.name]['size'] += file_stat.st_size

                    elif file_entry.is_symlink() and self._config.stat_follow_symlinks:
                        seen_files[real_path].setdefault('lnks', []).append(file_entry.path)

                    # file specific metrics
                    if self._config.filegauges and matched_files_length <= max_filegauge_balance:
                        self.log.debug('Matched files length: %s', matched_files_length)
                        filetags = ['{}:{}'.format(self._config.filetagname, join(root, file_entry.name))]
                        filetags.extend(dirtags)
                        self.gauge('system.disk.directory.file.bytes', file_stat.st_size, tags=filetags)
                        self.gauge(
                            'system.disk.directory.file.modified_sec_ago',
                            time() - file_stat.st_mtime,
                            tags=filetags,
                        )
                        self.gauge(
                            'system.disk.directory.file.created_sec_ago', time() - file_stat.st_ctime, tags=filetags
                        )
                        adjust_max_filegauge = True
                        self.log.debug(
                            'File stat output - size:%s mtime:%s ctime:%s',
                            str(file_stat.st_size),
                            str(file_stat.st_mtime),
                            str(file_stat.st_ctime),
                        )
                    elif submit_histograms:
                        self.histogram('system.disk.directory.file.bytes', file_stat.st_size, tags=dirtags)
                        self.histogram(
                            'system.disk.directory.file.modified_sec_ago', time() - file_stat.st_mtime, tags=dirtags
                        )
                        self.histogram(
                            'system.disk.directory.file.created_sec_ago', time() - file_stat.st_ctime, tags=dirtags
                        )
                        self.log.debug(
                            'File stat output histogram - size:%s mtime:%s ctime:%s',
                            str(file_stat.st_size),
                            str(file_stat.st_mtime),
                            str(file_stat.st_ctime),
                        )

            if adjust_max_filegauge:
                max_filegauge_balance -= matched_files_length

        # number of files
        self.gauge('system.disk.directory.files', directory_files, tags=dirtags)
        # number of folders
        self.gauge('system.disk.directory.folders', directory_folders, tags=dirtags)

        # total file size
        if not self._config.countonly:
            self.gauge('system.disk.directory.bytes', directory_bytes, tags=dirtags)
            self.log.debug("`countonly` not enabled: Collecting system.disk.directory.bytes metric.")

            # For troubleshooting. Contains files that contribute to system.disk.directory.bytes
            # Debug level is too common and could pollute the logs; trace level better for manual check runs.
            # seen_files = {'/path/to/real/file': [list of symlinks]}
            self.log.trace("Processed files: %s", seen_files)

    def _walk(self):
        """
        Wraps walker iteration to handle errors and recursive option.
        """
        walker = walk(self._config.abs_directory, self._config.follow_symlinks)

        while True:
            try:
                yield next(walker)
            except StopIteration:
                break
            except OSError as e:
                self.log.error("Error when traversing %s: %s", self._config.abs_directory, e)

            # Only visit the first directory when we don't want recursive search
            if not self._config.recursive:
                break
