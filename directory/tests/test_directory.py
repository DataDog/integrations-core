# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import shutil
import tempfile

import mock
import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dev.utils import create_file
from datadog_checks.dev.utils import temp_dir as temp_directory
from datadog_checks.directory import DirectoryCheck

from . import common

temp_dir = None
dir_check = DirectoryCheck('directory', {}, {})


def setup_module(module):
    """
    Generate a directory with a file structure for tests
    """
    module.temp_dir = tempfile.mkdtemp()

    # Create 10 files
    for i in range(0, 10):
        open(temp_dir + "/file_" + str(i), 'a').close()

    # Add 2 '.log' files
    open(temp_dir + "/log_1.log", 'a').close()
    open(temp_dir + "/log_2.log", 'a').close()

    # Create a subfolder and generate files into it
    os.makedirs(str(temp_dir) + "/subfolder")

    # Create 5 subfiles
    for i in range(0, 5):
        open(temp_dir + "/subfolder" + '/file_' + str(i), 'a').close()


def tearDown_module(module):
    shutil.rmtree(temp_dir)


def test_exclude_dirs(aggregator):
    with temp_directory() as td:
        exclude = ['node_modules', 'vendor']
        instance = {'directory': td, 'recursive': True, 'countonly': True, 'exclude_dirs': exclude}

        for ed in exclude:
            create_file(os.path.join(td, ed, 'file'))

        dir_check.check(instance)

    assert len(aggregator.metric_names) == 1


def test_directory_metrics(aggregator):
    """
    Directory metric coverage
    """
    config_stubs = common.get_config_stubs(temp_dir)
    countonly_stubs = common.get_config_stubs(temp_dir)

    # Try all the configurations in countonly mode as well
    for stub in countonly_stubs:
        stub['countonly'] = True

    for config in config_stubs:
        aggregator.reset()
        dir_check.check(config)
        dirtagname = config.get('dirtagname', "name")
        name = config.get('name', temp_dir)
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


def test_file_metrics(aggregator):
    """
    File metric coverage
    """
    config_stubs = common.get_config_stubs(temp_dir, filegauges=True)

    for config in config_stubs:
        aggregator.reset()
        dir_check.check(config)
        dirtagname = config.get('dirtagname', "name")
        name = config.get('name', temp_dir)
        filetagname = config.get('filetagname', "filename")
        dir_tags = [dirtagname + ":%s" % name, 'optional:tag1']

        # File metrics
        for mname in common.FILE_METRICS:
            if config.get('pattern') != "file_*":
                # 2 '*.log' files in 'temp_dir'
                for i in range(1, 3):
                    file_tag = [filetagname + ":%s" % os.path.normpath(temp_dir + "/log_" + str(i) + ".log")]
                    aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)

            if config.get('pattern') != "*.log":
                # Files in 'temp_dir'
                for i in range(0, 10):
                    file_tag = [filetagname + ":%s" % os.path.normpath(temp_dir + "/file_" + str(i))]
                    aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)

            if not config.get('pattern'):
                # Files in 'temp_dir/subfolder'
                if config.get('recursive'):
                    for i in range(0, 5):
                        file_tag = [filetagname + ":%s" % os.path.normpath(temp_dir + "/subfolder" + "/file_" + str(i))]
                        aggregator.assert_metric(mname, tags=dir_tags + file_tag, count=1)

        # Common metrics
        for mname in common.COMMON_METRICS:
            aggregator.assert_metric(mname, tags=dir_tags, count=1)

        # Raises when coverage < 100%
        assert aggregator.metrics_asserted_pct == 100.0


def test_non_existent_directory():
    """
    Missing or inaccessible directory coverage.
    """
    with pytest.raises(ConfigurationError):
        dir_check.check({'directory': '/non-existent/directory'})


def test_non_existent_directory_ignore_missing():
    config = {'directory': '/non-existent/directory', 'ignore_missing': True}
    dir_check._get_stats = mock.MagicMock()
    dir_check.check(config)
    dir_check._get_stats.assert_called_once()
