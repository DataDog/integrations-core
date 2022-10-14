# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging
import os
import shutil
import tempfile
from os import mkdir

import mock
import pytest

from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.dev.fs import create_file
from datadog_checks.dev.fs import temp_dir as temp_directory
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

    assert len(aggregator.metric_names) == 1


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

        # Raises when coverage < 100%
        assert aggregator.metrics_asserted_pct == 100.0


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
    aggregator.assert_metric('system.disk.directory.file.bytes', count=0)
    aggregator.assert_metric('system.disk.directory.file.modified_sec_ago', count=0)
    aggregator.assert_metric('system.disk.directory.file.created_sec_ago', count=0)

    aggregator.assert_all_metrics_covered()


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
    check._get_stats = mock.MagicMock()
    check.check(config)
    check._get_stats.assert_not_called()

    expected_tags = ['dir_name:/non-existent/directory', 'foo:bar']
    aggregator.assert_service_check('system.disk.directory.exists', DirectoryCheck.WARNING, tags=expected_tags)


def test_os_error_mid_walk_emits_error_and_continues(aggregator, monkeypatch, caplog):
    caplog.set_level(logging.WARNING)

    def mock_walk(folder, *args, **kwargs):
        from datadog_checks.directory.traverse import walk

        walker = walk(folder, *args, **kwargs)
        yield next(walker)
        raise OSError('Permission denied')

    monkeypatch.setattr('datadog_checks.directory.directory.walk', mock_walk)

    with temp_directory() as tdir:

        # Create folder
        mkdir(os.path.join(tdir, 'a_folder'))

        # Run Check
        instance = {'directory': tdir, 'recursive': True}
        check = DirectoryCheck('directory', {}, [instance])
        check.check(instance)

    assert 'Permission denied' in caplog.text


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


@pytest.mark.parametrize(
    'stat_follow_symlinks, expected_dir_size, expected_file_sizes',
    [
        pytest.param(True, 250, [('file50', 50), ('file100', 100), ('file100sym', 100)], id='follow_sym'),
        # file100sym = 8 + len(dir): that's the length of the symlink file
        pytest.param(
            False,
            lambda tdir: 150 + 8 + len(tdir),
            [('file50', 50), ('file100', 100), ('file100sym', lambda tdir: 8 + len(tdir))],
            id='not_follow_sym',
        ),
    ],
)
def test_stat_follow_symlinks(aggregator, stat_follow_symlinks, expected_dir_size, expected_file_sizes):
    def flatten_value(value):
        if callable(value):
            return value(tdir)
        return value

    with temp_directory() as tdir:

        # Setup dir and files
        file50 = os.path.join(tdir, 'file50')
        file100 = os.path.join(tdir, 'file100')
        file100sym = os.path.join(tdir, 'file100sym')

        with open(file50, 'w') as f:
            f.write('0' * 50)
        with open(file100, 'w') as f:
            f.write('0' * 100)

        os.symlink(file100, file100sym)

        # Run Check
        instance = {
            'directory': tdir,
            'recursive': True,
            'filegauges': True,
            'stat_follow_symlinks': stat_follow_symlinks,
        }
        check = DirectoryCheck('directory', {}, [instance])
        check.check(instance)

        common_tags = ['name:{}'.format(tdir)]
        aggregator.assert_metric(
            'system.disk.directory.bytes', value=flatten_value(expected_dir_size), tags=common_tags
        )
        for filename, size in expected_file_sizes:
            tags = common_tags + ['filename:{}'.format(os.path.join(tdir, filename))]
            aggregator.assert_metric('system.disk.directory.file.bytes', value=flatten_value(size), tags=tags)
