# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.dev import get_here

CHECK_NAME = 'directory'
HERE = get_here()

FILE_METRICS = [
    "system.disk.directory.file.bytes",
    "system.disk.directory.file.modified_sec_ago",
    "system.disk.directory.file.created_sec_ago",
]

FOLDER_METRICS = [
    "system.disk.directory.folder.modified_sec_ago",
    "system.disk.directory.folder.created_sec_ago",
]

DIR_METRICS = ["system.disk.directory.files", "system.disk.directory.folders", "system.disk.directory.bytes"]

EXPECTED_METRICS = FILE_METRICS + DIR_METRICS

EXPECTED_TAGS = ['name:.', 'optional:tag1']


def get_config_stubs(dir_name, filegauges=False, collect_folder_stats=False):
    """
    Helper to generate configs from a directory name
    """
    return [
        {
            'directory': dir_name,
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
        {
            'directory': dir_name,
            'name': "my_beloved_directory",
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
        {
            'directory': dir_name,
            'dirtagname': "directory_custom_tagname",
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
        {
            'directory': dir_name,
            'filetagname': "file_custom_tagname",
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
        {
            'directory': dir_name,
            'dirtagname': "recursive_check",
            'recursive': True,
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
        {
            'directory': dir_name,
            'dirtagname': "recursive_pattern_check",
            'pattern': "*.log",
            'recursive': True,
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
        {
            'directory': dir_name,
            'dirtagname': "glob_pattern_check",
            'pattern': "*.log",
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
        {
            'directory': dir_name,
            'dirtagname': "relative_pattern_check",
            'pattern': "file_*",
            'filegauges': filegauges,
            'collect_folder_stats': collect_folder_stats,
            'tags': ['optional:tag1'],
        },
    ]
