# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import platform
import sys

import six

try:
    from os import scandir
except ImportError:
    from scandir import scandir


def _walk(top, onerror=None, followlinks=False):
    """A simplified and modified version of stdlib's `os.walk` that yields the
    `os.DirEntry` objects that `scandir` produces during traversal instead of paths as
    strings.
    """
    # This implementation is based on https://github.com/python/cpython/blob/3.8/Lib/os.py#L280.

    # This is a significant optimization for our use case (particularly on Windows) that
    # justifies maintaining our own version of the function instead of using the
    # stdlib's one directly. We need to stat every file to collect useful data, and the
    # following quote from the docs
    # (https://docs.python.org/3.8/library/os.html#os.scandir) explains very well why we
    # want to keep those `os.DirEntry` objects:

    # Using `scandir()` instead of `listdir()` can significantly increase the performance of
    # code that also needs file type or file attribute information, because os.DirEntry
    # objects expose this information if the operating system provides it when scanning a
    # directory. All `os.DirEntry` methods may perform a system call, but is_dir() and
    # is_file() usually only require a system call for symbolic links; os.DirEntry.stat()
    # always requires a system call on Unix but only requires one for symbolic links on
    # Windows.

    dirs = []
    nondirs = []

    try:
        scandir_iter = scandir(top)
    except OSError as error:
        if onerror is not None:
            onerror(error)
        return

    # Avoid repeated global lookups.
    get_next = next

    while True:
        try:
            entry = get_next(scandir_iter)
        except StopIteration:
            break
        except OSError as error:
            if onerror is not None:
                onerror(error)
            continue

        try:
            is_dir = entry.is_dir(follow_symlinks=followlinks)
        except OSError:
            is_dir = False

        if is_dir:
            dirs.append(entry)
        else:
            nondirs.append(entry)

    yield top, dirs, nondirs

    for dir_entry in dirs:
        for entry in walk(dir_entry.path, onerror, followlinks):
            yield entry


if six.PY3 or platform.system() != 'Windows':
    walk = _walk
else:
    # Fix for broken unicode handling on Windows on Python 2.x, see:
    # https://github.com/benhoyt/scandir/issues/54
    file_system_encoding = sys.getfilesystemencoding()

    def walk(top, onerror, followlinks):
        if isinstance(top, bytes):
            top = top.decode(file_system_encoding)
        return _walk(top, onerror, followlinks)
