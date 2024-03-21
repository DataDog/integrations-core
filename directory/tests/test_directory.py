# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging
import os
import shutil
import tempfile
from os import mkdir

import pytest

from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.dev.fs import create_file
from datadog_checks.dev.fs import temp_dir as temp_directory
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.directory import DirectoryCheck

from . import common

temp_dir = None


def setup_module(module):
    """
    Generate a directory with a file structure for tests
    """

    module.temp_dir = tempfile.mkdtemp()

    # Create folder structure
    os.makedirs(str(temp_dir) + "/main/subfolder")
    os.makedirs(str(temp_dir) + "/main/subfolder/subsubfolder")
    os.makedirs(str(temp_dir) + "/main/othersubfolder")
    os.makedirs(str(temp_dir) + "/many/subfolder")

    # Create 10 files in main
    for i in range(0, 10):
        open(temp_dir + "/main/file_" + str(i), 'a').close()

    # Add 2 '.log' files in main
    open(temp_dir + "/main/log_1.log", 'a').close()
    open(temp_dir + "/main/log_2.log", 'a').close()

    # Create 5 subfiles in main
    for i in range(0, 5):
        open(temp_dir + "/main/subfolder" + '/file_' + str(i), 'a').close()

    # Create 50 files in many
    for i in range(0, 50):
        if i < 5:
            # First 5 files in list match `*.log`
            open(temp_dir + "/many" + '/aalog_' + str(i) + '.log', 'a').close()
        elif i >= 45:
            # Last 5 files in list match `*.log`
            open(temp_dir + "/many" + '/zzlog_' + str(i) + '.log', 'a').close()
        else:
            # Remaining 40 files in between match `file_*`
            open(temp_dir + "/many" + '/file_' + str(i), 'a').close()

    # Create 15 subfiles in many
    for i in range(0, 15):
        if i < 2:
            # First 2 files in list match `*.log`
            open(temp_dir + "/many/subfolder" + '/aalog_' + str(i) + '.log', 'a').close()
        elif i >= 12:
            # Last 3 files in list match `*.log`
            open(temp_dir + "/many/subfolder" + '/zzlog_' + str(i) + '.log', 'a').close()
        else:
            # Remaining 10 files in between match `file_*`
            open(temp_dir + "/many/subfolder" + '/file_' + str(i), 'a').close()


def tearDown_module(module):
    shutil.rmtree(temp_dir)


def test_exclude_dirs(aggregator):
    with temp_directory() as td:
        exclude = ['node_modules', 'vendor']
        instance = {'directory': td, 'recursive': True, 'countonly': True, 'exclude_dirs': exclude}

        for ed in exclude:
            create_file(os.path.join(td, ed, 'file'))

        dir_check = DirectoryCheck('directory', {}, [instance])
        dir_check.check(instance)

    aggregator.assert_metric("system.disk.directory.folders", count=1, value=0)
    aggregator.assert_metric("system.disk.directory.files", count=1, value=0)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_directory_metrics(aggregator):
    """
    Directory metric coverage
    """
    config_stubs = common.get_config_stubs(temp_dir + "/main")
    countonly_stubs = common.get_config_stubs(temp_dir + "/main")

    # Try all the configurations in countonly mode as well
    for stub in countonly_stubs:
        stub['countonly'] = True

    for config in config_stubs:
        aggregator.reset()
        dir_check = DirectoryCheck('directory', {}, [config])
        dir_check.check(config)
        dirtagname = config.get('dirtagname', "name")
        name = config.get('name', temp_dir + "/main")
        dir_tags = [dirtagname + ":%s" % name, 'optional:tag1']

        # 'recursive' and 'pattern' parameters
        if config.get('pattern') == "*.log":
            # 2 '*.log' files in 'temp_dir'
            aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=2)
        elif config.get('pattern') == "file_*":
            # 10 'file_*' files in 'temp_dir'
            aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=10)
        elif config.get('recursive'):
            # 12 files in 'temp_dir' + 5 files in 'tempdir/subfolder'
            aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=17)
        else:
            # 12 files in 'temp_dir'
            aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=12)

        if config.get('recursive'):
            aggregator.assert_metric("system.disk.directory.folders", tags=dir_tags, count=1, value=3)
        else:
            aggregator.assert_metric("system.disk.directory.folders", tags=dir_tags, count=1, value=2)

    # Raises when coverage < 100%
    aggregator.metrics_asserted_pct == 100.0


def test_directory_metrics_many(aggregator):
    """
    Directory metric coverage
    """
    config_stubs = common.get_config_stubs(temp_dir + "/many")
    countonly_stubs = common.get_config_stubs(temp_dir + "/many")

    # Try all the configurations in countonly mode as well
    for stub in countonly_stubs:
        stub['countonly'] = True

    for config in config_stubs:
        aggregator.reset()
        dir_check = DirectoryCheck('directory', {}, [config])
        dir_check.check(config)
        dirtagname = config.get('dirtagname', "name")
        name = config.get('name', temp_dir + "/many")
        dir_tags = [dirtagname + ":%s" % name, 'optional:tag1']

        # 'recursive' and 'pattern' parameters
        if config.get('pattern') == "*.log":
            # 10 '*.log' files in 'temp_dir/many'
            if config.get('recursive'):
                aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=15)
            else:
                aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=10)
        elif config.get('pattern') == "file_*":
            # 40 'file_*' files in 'temp_dir/many'
            aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=40)
        elif config.get('recursive'):
            # 50 files in 'temp_dir/many' + 15 files in 'temp_dir/many/subfolder'
            aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=65)
        else:
            # 50 files in 'temp_dir/many'
            aggregator.assert_metric("system.disk.directory.files", tags=dir_tags, count=1, value=50)

    # Raises when coverage < 100%
    aggregator.metrics_asserted_pct == 100.0


def test_file_metrics(aggregator):
    """
    File metric coverage
    """
    config_stubs = common.get_config_stubs(temp_dir + "/main", filegauges=True)

    for config in config_stubs:
        aggregator.reset()
        dir_check = DirectoryCheck('directory', {}, [config])
        dir_check.check(config)
        dirtagname = config.get('dirtagname', "name")
        name = config.get('name', temp_dir + "/main")
        filetagname = config.get('filetagname', "filename")
        dir_tags = [dirtagname + ":%s" % name, 'optional:tag1']

        # File metrics
        for mname in common.FILE_METRICS:
            if config.get('pattern') != "file_*":
                # 2 '*.log' files in 'temp_dir'
                for i in range(1, 3):
                    file_tag = [filetagname + ":%s" % os.path.normpath(temp_dir + "/main/log_" + str(i) + ".log")]
                    aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)

            if config.get('pattern') != "*.log":
                # Files in 'temp_dir'
                for i in range(0, 10):
                    file_tag = [filetagname + ":%s" % os.path.normpath(temp_dir + "/main/file_" + str(i))]
                    aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)

            if not config.get('pattern'):
                # Files in 'temp_dir/subfolder'
                if config.get('recursive'):
                    for i in range(0, 5):
                        file_tag = [
                            filetagname + ":%s" % os.path.normpath(temp_dir + "/main/subfolder" + "/file_" + str(i))
                        ]
                        aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)

        # Common metrics
        for mname in common.DIR_METRICS:
            aggregator.assert_metric(mname, tags=dir_tags, count=1)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_file_metrics_many(aggregator):
    """
    File metric coverage
    """
    config_stubs = common.get_config_stubs(temp_dir + "/many", filegauges=True)

    for config in config_stubs:
        aggregator.reset()
        dir_check = DirectoryCheck('directory', {}, [config])
        dir_check.check(config)
        dirtagname = config.get('dirtagname', "name")
        name = config.get('name', temp_dir + "/many")
        filetagname = config.get('filetagname', "filename")
        dir_tags = [dirtagname + ":%s" % name, 'optional:tag1']

        # File metrics
        for mname in common.FILE_METRICS:
            if config.get('pattern') == "*.log":
                # 10 '*.log' files in 'temp_dir/many'
                for i in range(0, 50):
                    if i < 5:
                        file_tag = [filetagname + ":%s" % os.path.normpath("{}/many/aalog_{}.log".format(temp_dir, i))]
                    elif i >= 45:

                        file_tag = [filetagname + ":%s" % os.path.normpath("{}/many/zzlog_{}.log".format(temp_dir, i))]
                    else:
                        continue
                    aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)

            if config.get('pattern') == "file_*":
                # file_* in 'temp_dir/many' > 20 therefore no `filename`
                aggregator.assert_metric(mname, tags=dir_tags, count=40)

            if not config.get('pattern'):
                # Files in 'temp_dir/many/'
                file_tag = []
                if config.get('recursive'):

                    for i in range(0, 15):
                        # Files in 'temp_dir/many/subfolder' < 20 therefore all gets `filename`
                        if i < 2:
                            file_tag = [
                                filetagname
                                + ":%s" % os.path.normpath(temp_dir + "/many/subfolder" + "/aalog_" + str(i) + '.log')
                            ]
                        elif i >= 12:
                            file_tag = [
                                filetagname
                                + ":%s" % os.path.normpath(temp_dir + "/many/subfolder" + "/zzlog_" + str(i) + '.log')
                            ]
                        else:
                            file_tag = [
                                filetagname + ":%s" % os.path.normpath(temp_dir + "/many/subfolder" + "/file_" + str(i))
                            ]
                        aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)
                    # Remaining files in 'temp_dir/many/` > 20 therefore no `filename`
                    aggregator.assert_metric(mname, tags=dir_tags, count=50)
                else:
                    aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=50)

        # Common metrics
        for mname in common.DIR_METRICS:
            aggregator.assert_metric(mname, tags=dir_tags, count=1)

        # Raises when coverage < 100%
        assert aggregator.metrics_asserted_pct == 100.0


def test_omit_histograms(aggregator, dd_run_check):
    check = DirectoryCheck('directory', {}, [{'directory': temp_dir + '/main', 'submit_histograms': False}])
    dd_run_check(check)

    aggregator.assert_metric('system.disk.directory.bytes', count=1)
    aggregator.assert_metric('system.disk.directory.files', count=1)
    aggregator.assert_metric('system.disk.directory.folders', count=1)
    aggregator.assert_metric('system.disk.directory.file.bytes', count=0)
    aggregator.assert_metric('system.disk.directory.file.modified_sec_ago', count=0)
    aggregator.assert_metric('system.disk.directory.file.created_sec_ago', count=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_non_existent_directory(aggregator):
    """
    Missing or inaccessible directory coverage.
    """
    config = {'directory': '/non-existent/directory', 'tags': ['foo:bar']}
    with pytest.raises(CheckException):
        dir_check = DirectoryCheck('directory', {}, [config])
        dir_check.check(config)
    expected_tags = ['dir_name:/non-existent/directory', 'foo:bar']
    aggregator.assert_service_check('system.disk.directory.exists', DirectoryCheck.WARNING, tags=expected_tags)


def test_missing_directory_config():
    with pytest.raises(ConfigurationError):
        DirectoryCheck('directory', {}, [{}])


def test_non_existent_directory_ignore_missing(aggregator):
    config = {'directory': '/non-existent/directory', 'ignore_missing': True, 'tags': ['foo:bar']}
    check = DirectoryCheck('directory', {}, [config])
    check.check(config)

    expected_tags = ['dir_name:/non-existent/directory', 'foo:bar']
    aggregator.assert_service_check('system.disk.directory.exists', DirectoryCheck.WARNING, tags=expected_tags)


def test_os_error_mid_walk_emits_error_and_continues(aggregator, caplog):
    caplog.set_level(logging.WARNING)

    # Test that we continue on traversal by having more than a single error-producing entry.
    # The stdlib's tests rename a file mid-walk to simulate this, but we can't do that since
    # we're testing the walk function indirectly and can't control it.
    #
    # At least we can generate an error on folders by creating them without read permissions.
    # This does leave one of the code paths untested (getting the next item from a folder,
    # precisely, the scenario that the stdlib simulates).
    #
    # Finally, the order of traversal is not guaranteed. We get around that by introducing two
    # problematic folders and checking that both errors are indeed logged.

    with temp_directory() as tdir:
        # Create two folders with no read permission
        os.makedirs(os.path.join(tdir, 'bad_folder_a'), mode=0o377)
        os.makedirs(os.path.join(tdir, 'bad_folder_b'), mode=0o377)
        # Create a folder with normal permissions, and a file inside
        os.makedirs(os.path.join(tdir, 'ok'))
        with open(os.path.join(tdir, 'ok', 'file'), 'w') as f:
            f.write('')

        # Run Check
        instance = {'directory': tdir, 'recursive': True}
        check = DirectoryCheck('directory', {}, [instance])
        check.check(instance)

        # Reset permissions for folders to allow cleanup
        os.chmod(os.path.join(tdir, 'bad_folder_a'), 0o777)
        os.chmod(os.path.join(tdir, 'bad_folder_b'), 0o777)

    aggregator.assert_metric("system.disk.directory.files", count=1, value=1)

    permission_denied_log_lines = [line for line in caplog.text.splitlines() if 'Permission denied' in line]
    assert len(permission_denied_log_lines) == 2
    assert 'bad_folder_a' in caplog.text
    assert 'bad_folder_b' in caplog.text


def test_no_recursive_symlink_loop(aggregator):
    with temp_directory() as tdir:

        # Setup dir and files
        dir2 = os.path.join(tdir, 'fixture_dir2')
        dir3 = os.path.join(tdir, 'fixture_dir2', 'fixture_dir3')
        mkdir(dir2)
        mkdir(dir3)
        open(os.path.join(tdir, 'level1file'), 'w').close()
        open(os.path.join(dir2, 'level2file'), 'w').close()
        open(os.path.join(dir3, 'level3file'), 'w').close()
        os.symlink(tdir, os.path.join(dir3, 'symdir'))

        # Run Check
        instance = {'directory': tdir, 'recursive': True, 'filegauges': True, 'follow_symlinks': False}
        check = DirectoryCheck('directory', {}, [instance])
        check.check(instance)

        # Assert no warning
        assert len(check.warnings) == 0

        # Assert metrics
        files = [
            ['level1file'],
            ['fixture_dir2', 'level2file'],
            ['fixture_dir2', 'fixture_dir3', 'level3file'],
            ['fixture_dir2', 'fixture_dir3', 'symdir'],
        ]
        for file in files:
            for metric in common.FILE_METRICS:
                tags = ['name:{}'.format(tdir), 'filename:{}'.format(os.path.join(tdir, *file))]
                aggregator.assert_metric(metric, count=1, tags=tags)
        for metric in common.DIR_METRICS:
            tags = ['name:{}'.format(tdir)]
            aggregator.assert_metric(metric, count=1, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    'stat_follow_symlinks, expected_dir_size, expected_file_sizes',
    [
        # du --apparent-size /path/ -abc -L
        # aka follow symlinks - dedups total directory size
        pytest.param(
            True,
            2500,
            [
                ('file500', 500),
                ('file1000', 1000),
                ('file1000sym', 1000),  # Should not count; target file lives under same directory
                ('otherfile1000sym', 1000),
            ],
            id='follow_sym',
        ),
        # du --apparent-size /path/ -abc -P
        # https://docs.python.org/3/library/os.html#os.stat_result.st_size
        # len(tdir + '/path') = 21 = target_dir
        # len('/file1000') = 9 = target file
        pytest.param(
            False,
            lambda tdir: 1500 + len(tdir + '/file1000') * 2,
            [
                ('file500', 500),
                ('file1000', 1000),
                ('file1000sym', lambda tdir: len(tdir + '/file1000')),
                ('otherfile1000sym', lambda tdir: len(tdir + '/file1000')),
            ],
            id='not_follow_sym',
        ),
    ],
)
def test_stat_follow_symlinks(aggregator, stat_follow_symlinks, expected_dir_size, expected_file_sizes):
    def flatten_value(value):
        if callable(value):
            return value(target_dir)
        return value

    with temp_directory() as tdir:

        # Setup dir and files
        os.makedirs(str(tdir) + "/main")
        os.makedirs(str(tdir) + "/othr")

        # Setup files
        file500 = os.path.join(tdir + '/main', 'file500')
        file1000 = os.path.join(tdir + '/main', 'file1000')
        file1000sym = os.path.join(tdir + '/main', 'file1000sym')
        otherfile1000 = os.path.join(tdir + '/othr', 'file1000')
        otherfile1000sym = os.path.join(tdir + '/main', 'otherfile1000sym')

        with open(file500, 'w') as f:
            f.write('0' * 500)
        with open(file1000, 'w') as f:
            f.write('0' * 1000)
        with open(otherfile1000, 'w') as f:
            f.write('0' * 1000)

        os.symlink(file1000, file1000sym)
        os.symlink(otherfile1000, otherfile1000sym)

        # Run Check
        target_dir = tdir + '/main'
        instance = {
            'directory': target_dir,
            'recursive': True,
            'filegauges': True,
            'stat_follow_symlinks': stat_follow_symlinks,
        }
        check = DirectoryCheck('directory', {}, [instance])
        check.check(instance)

        common_tags = ['name:{}'.format(target_dir)]
        aggregator.assert_metric(
            'system.disk.directory.bytes', value=flatten_value(expected_dir_size), tags=common_tags
        )
        for filename, size in expected_file_sizes:
            tags = common_tags + ['filename:{}'.format(os.path.join(target_dir, filename))]
            aggregator.assert_metric('system.disk.directory.file.bytes', value=flatten_value(size), tags=tags)
