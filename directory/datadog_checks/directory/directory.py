# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from fnmatch import fnmatch
from os.path import abspath, exists, join, relpath
from re import compile as re_compile
from time import time

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative
from .traverse import walk


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

    def check(self, instance):
        try:
            directory = instance['directory']
        except KeyError:
            raise Exception('DirectoryCheck: missing `directory` in config')

        abs_directory = abspath(directory)
        name = instance.get('name', directory)
        pattern = instance.get('pattern')
        exclude_dirs = instance.get('exclude_dirs', [])
        exclude_dirs_pattern = re_compile('|'.join(exclude_dirs)) if exclude_dirs else None
        dirs_patterns_full = is_affirmative(instance.get('dirs_patterns_full', False))
        recursive = is_affirmative(instance.get('recursive', False))
        dirtagname = instance.get('dirtagname', 'name')
        filetagname = instance.get('filetagname', 'filename')
        filegauges = is_affirmative(instance.get('filegauges', False))
        countonly = is_affirmative(instance.get('countonly', False))
        ignore_missing = is_affirmative(instance.get('ignore_missing', False))
        custom_tags = instance.get('tags', [])

        if not exists(abs_directory):
            if ignore_missing:
                self.log.info(
                    'DirectoryCheck: the directory `{}` does not exist. Skipping.'.format(abs_directory)
                )
                return

            raise Exception(
                'DirectoryCheck: the directory `{}` does not exist. Skipping.'.format(abs_directory)
            )

        self._get_stats(
            abs_directory,
            name,
            dirtagname,
            filetagname,
            filegauges,
            pattern,
            exclude_dirs_pattern,
            dirs_patterns_full,
            recursive,
            countonly,
            custom_tags
        )

    def _get_stats(
        self,
        directory,
        name,
        dirtagname,
        filetagname,
        filegauges,
        pattern,
        exclude_dirs_pattern,
        dirs_patterns_full,
        recursive,
        countonly,
        tags
    ):
        dirtags = ['{}:{}'.format(dirtagname, name)]
        dirtags.extend(tags)
        directory_bytes = 0
        directory_files = 0

        # If we do not want to recursively search sub-directories only get the root.
        walker = walk(directory) if recursive else (next(walk(directory)), )

        # Avoid repeated global lookups.
        get_length = len

        for root, dirs, files in walker:
            directory_files += get_length(files)

            if exclude_dirs_pattern is not None:
                if dirs_patterns_full:
                    dirs[:] = [d for d in dirs if not exclude_dirs_pattern.search(d.path)]
                else:
                    dirs[:] = [d for d in dirs if not exclude_dirs_pattern.search(d.name)]

            for file_entry in files:
                if pattern:
                    # Check if the path of the file relative to the directory
                    # matches the pattern. Also check if the absolute path of the
                    # filename matches the pattern, for compatibility with previous
                    # agent versions.
                    filename = join(root, file_entry.name)
                    if not (
                        fnmatch(filename, pattern) or
                        fnmatch(relpath(filename, directory), pattern)
                    ):
                        directory_files -= 1
                        continue

                # We're just looking to count the files.
                if countonly:
                    continue

                try:
                    file_stat = file_entry.stat()

                except OSError as ose:
                    self.warning(
                        'DirectoryCheck: could not stat file {} - {}'.format(join(root, file_entry.name), ose)
                    )
                else:
                    # file specific metrics
                    directory_bytes += file_stat.st_size
                    if filegauges and directory_files <= 20:
                        filetags = ['{}:{}'.format(filetagname, join(root, file_entry.name))]
                        filetags.extend(dirtags)
                        self.gauge(
                            'system.disk.directory.file.bytes',
                            file_stat.st_size,
                            tags=filetags
                        )
                        self.gauge(
                            'system.disk.directory.file.modified_sec_ago',
                            time() - file_stat.st_mtime,
                            tags=filetags
                        )
                        self.gauge(
                            'system.disk.directory.file.created_sec_ago',
                            time() - file_stat.st_ctime,
                            tags=filetags
                        )
                    else:
                        self.histogram(
                            'system.disk.directory.file.bytes',
                            file_stat.st_size,
                            tags=dirtags
                        )
                        self.histogram(
                            'system.disk.directory.file.modified_sec_ago',
                            time() - file_stat.st_mtime,
                            tags=dirtags
                        )
                        self.histogram(
                            'system.disk.directory.file.created_sec_ago',
                            time() - file_stat.st_ctime,
                            tags=dirtags
                        )

        # number of files
        self.gauge('system.disk.directory.files', directory_files, tags=dirtags)

        # total file size
        if not countonly:
            self.gauge('system.disk.directory.bytes', directory_bytes, tags=dirtags)
