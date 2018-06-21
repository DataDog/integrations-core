# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil
import subprocess
import sys
import tempfile

from datadog_checks.directory import DirectoryCheck


def test_run(benchmark):
    temp_dir = tempfile.mkdtemp()
    command = [sys.executable, '-m', 'virtualenv', temp_dir]
    instance = {'directory': temp_dir, 'recursive': True}

    try:
        subprocess.call(command)
        c = DirectoryCheck('directory', None, {}, [instance])

        benchmark(c.check, instance)
    finally:
        shutil.rmtree(temp_dir)
