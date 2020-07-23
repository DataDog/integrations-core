# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import inspect
import pdb
import sys


class Debugger(pdb.Pdb):
    """Modified debugger that assumes the existence of predefined break points."""

    def set_trace(self, frame=None):
        """See https://github.com/python/cpython/blob/b02774f42108aaf18eb19865472c8d5cd95b5f11/Lib/bdb.py#L319-L332"""
        self.reset()

        if frame is None:
            frame = sys._getframe().f_back

        while frame:
            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back

        # Automatically proceed to next break point
        self.set_continue()

        sys.settrace(self.trace_dispatch)


def enter_pdb(f, line=0, args=(), kwargs=None):
    line = int(line)

    if kwargs is None:
        kwargs = {}

    file_name = inspect.getfile(f)
    lines, def_line = inspect.getsourcelines(f)

    start = def_line + 1
    stop = def_line + len(lines)

    # Get rid of the declaration (assuming it spans only one line)
    del lines[:1]

    # Start of the function
    if line == 0:
        line = get_first_statement(lines, start)
    # End of the function
    elif line == -1:
        line = abs(get_first_statement(reversed(lines), -(stop - 1)))
    # Specific line number of the file where the function is defined
    else:
        # Ensure the line is actually within the function
        if line not in range(start, stop):
            raise ValueError('Line {} is not part of the check method.'.format(line))

        elif not is_statement(lines[line - def_line - 1]):
            raise ValueError('There is nothing to execute on line {}.'.format(line))

    debugger = Debugger()
    debugger.set_break(file_name, line)
    debugger.set_trace()

    f(*args, **kwargs)


def get_first_statement(lines, start):
    for i, line in enumerate(lines, start):
        if is_statement(line):
            return i
    else:
        raise ValueError('There is nothing to execute on line {}.'.format(abs(start)))


def is_statement(line):
    line = line.strip()

    # Blank lines, comments, or docstrings
    if not line or line.startswith(('#', '"', "'")):
        return False

    return True
