# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gc
import linecache
import os
from datetime import datetime

from binary import BinaryUnits, convert_units

from .common import METRIC_PROFILE_NAMESPACE

try:
    import tracemalloc
except ImportError:
    tracemalloc = None

DEFAULT_FRAMES = 100
DEFAULT_GC = False
DEFAULT_COMBINE = False
DEFAULT_SORT_KEY = 'lineno'
DEFAULT_KEY_LIMIT = 30
DEFAULT_DIFF_ORDER = 'absolute'
DEFAULT_UNIT = 'dynamic'
DEFAULT_VERBOSITY = False

# The order matters
VALID_PACKAGE_ROOTS = ('datadog_checks', 'site-packages', 'lib', 'Lib')

# Starting in Python 3.7 frames are sorted from the oldest to the most recent
MOST_RECENT_FRAME = -1


class MemoryProfileMetric(object):
    __slots__ = ('name', 'value')

    def __init__(self, name, value):
        self.name = '{}.memory.{}'.format(METRIC_PROFILE_NAMESPACE, name)
        self.value = float(value)


def get_sign(n):
    return '-' if n < 0 else '+'


def get_timestamp_filename(prefix):
    return '{}_{}'.format(prefix, datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S_%f'))


def parse_package_path(path):
    # If possible, replace `/path/to/<PACKAGES_ROOT>/package/file.py` with `package/file.py`
    # where the root is either:
    #
    # 1. datadog_checks namespace
    # 2. site-packages
    # 3. stdlib
    path_parts = path.split(os.sep)

    # We reuse the already split path to avoid a complex regular expression
    package_root = None
    for valid_root in VALID_PACKAGE_ROOTS:
        if valid_root in path_parts:
            package_root = valid_root
            break

    if package_root:
        check_package_parts = path_parts[path_parts.index(package_root) + 1 :]
        if check_package_parts:
            path = os.sep.join(check_package_parts)

    return path


def get_unit(unit):
    return getattr(BinaryUnits, unit.upper().replace('I', ''), BinaryUnits.B)


def format_units(unit, amount, unit_repr):
    # Dynamic based on the number of bytes
    if unit is None:
        unit = get_unit(unit_repr)

    if unit < BinaryUnits.KB:
        return '%d' % amount, unit_repr
    elif unit < BinaryUnits.MB:
        return '%.2f' % amount, unit_repr
    else:
        return '%.3f' % amount, unit_repr


def get_unit_formatter(unit):
    if unit == 'dynamic':
        unit = None
    else:
        unit = get_unit(unit)

    return lambda n: format_units(unit, *convert_units(n, to=unit))


def gather_top(metrics, path, snapshot, unit_formatter, key_type, limit, cumulative):
    top_stats = snapshot.statistics(key_type, cumulative=cumulative)

    if not path:
        total = sum(stat.size for stat in top_stats)
        metrics.append(MemoryProfileMetric('check_run_alloc', total))
        return

    with open(path, 'w', encoding='utf-8') as f:
        f.write('Top {} lines\n'.format(limit))

        for index, stat in enumerate(top_stats[:limit], 1):
            frame = stat.traceback[MOST_RECENT_FRAME]

            amount, unit = unit_formatter(stat.size)
            f.write(
                '\n#{}: {}:{}: {} {}\n'.format(index, parse_package_path(frame.filename), frame.lineno, amount, unit)
            )

            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                f.write(' {}  {}\n'.format(' ' * len(str(index)), line))

        f.write('\n')

        other = top_stats[limit:]
        if other:
            size = sum(stat.size for stat in other)
            amount, unit = unit_formatter(size)
            f.write('{} other: {} {}\n'.format(len(other), amount, unit))

        total = sum(stat.size for stat in top_stats)
        amount, unit = unit_formatter(total)
        f.write('Total allocated size: {} {}\n'.format(amount, unit))

    metrics.append(MemoryProfileMetric('check_run_alloc', total))


def gather_diff(
    metrics, path, current_snapshot, previous_snapshot, unit_formatter, key_type, limit, cumulative, diff_order
):
    top_stats = current_snapshot.compare_to(previous_snapshot, key_type=key_type, cumulative=cumulative)

    if diff_order == 'positive':
        # Keep the default behavior, but add precedence for memory increases
        top_stats = sorted(top_stats, key=lambda stat: (int(stat.size_diff > 0),) + stat._sort_key())[::-1]

    with open(path, 'w', encoding='utf-8') as f:
        f.write('Top {} line diffs\n'.format(limit))

        index = 0
        for stat in top_stats[:limit]:
            # Disregard lines that have no diff as the top lines are already shown by the snapshot files
            if not stat.size_diff:
                continue

            index += 1
            frame = stat.traceback[MOST_RECENT_FRAME]

            amount, unit = unit_formatter(abs(stat.size_diff))
            f.write(
                '\n#{}: {}:{}: {}{} {}\n'.format(
                    index, parse_package_path(frame.filename), frame.lineno, get_sign(stat.size_diff), amount, unit
                )
            )

            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                f.write(' {}  {}\n'.format(' ' * len(str(index)), line))

        f.write('\n')

        other = top_stats[limit:]
        if other:
            size = sum(stat.size_diff for stat in other)
            amount, unit = unit_formatter(abs(size))
            f.write('{} other: {}{} {}\n'.format(len(other), get_sign(size), amount, unit))

        total = sum(stat.size_diff for stat in top_stats)
        amount, unit = unit_formatter(abs(total))
        f.write('Total difference: {}{} {}\n'.format(get_sign(total), amount, unit))


def profile_memory(f, config, namespaces=None, args=(), kwargs=None):
    """
    This will track all memory (de-)allocations that occur during the lifetime of function ``f``.
    The only assumption is that the ``config`` dictionary has an entry ``profile_memory`` that
    points to a directory with which to output the information for later consumption.

    The available options (without prefix) are:

      - frames: the number of stack frames to consider
      - gc: whether or not to run the garbage collector before each snapshot to remove noise
      - combine: whether or not to aggregate over all traceback frames. useful only to tell
                 which particular usage of a function triggered areas of interest
      - sort: what to group results by between: lineno | filename | traceback
      - limit: the maximum number of sorted results to show
      - diff: how to order diff results between:
                * absolute: absolute value of the difference between consecutive snapshots
                * positive: same as absolute, but memory increases will be shown first
      - filters: comma-separated list of file path glob patterns to filter by
      - unit: the binary unit to represent memory usage (kib, mb, etc.). the default is dynamic
      - verbose: whether or not to include potentially noisy sources

    :param f: the function to trace
    :param config: a dictionary of options prefixed by ``profile_memory_``
    :param namespaces: if specified, additional sub-directories under ``profile_memory`` root directory
    :param args: arguments to pass to function ``f``
    :param kwargs: keyword arguments to pass to function ``f``
    :return:
    """
    if kwargs is None:
        kwargs = {}

    frames = int(config.get('profile_memory_frames', DEFAULT_FRAMES))
    run_gc = bool(int(config.get('profile_memory_gc', DEFAULT_GC)))

    try:
        gc.disable()
        gc.collect()

        tracemalloc.start(frames)

        f(*args, **kwargs)

        if run_gc:
            gc.collect()

        snapshot = tracemalloc.take_snapshot()
    finally:
        tracemalloc.stop()
        gc.enable()

    verbose = bool(int(config.get('profile_memory_verbose', DEFAULT_VERBOSITY)))
    if not verbose:
        snapshot = snapshot.filter_traces(
            (
                tracemalloc.Filter(False, '<frozen importlib._bootstrap>'),
                tracemalloc.Filter(False, '<frozen importlib._bootstrap_external>'),
                tracemalloc.Filter(False, '<unknown>'),
                tracemalloc.Filter(False, tracemalloc.__file__),
                tracemalloc.Filter(False, __file__),
            )
        )

    filters = config.get('profile_memory_filters')
    if filters:
        snapshot = snapshot.filter_traces([tracemalloc.Filter(True, pattern) for pattern in filters.split(',')])

    combine = bool(int(config.get('profile_memory_combine', DEFAULT_COMBINE)))
    sort_by = config.get('profile_memory_sort', DEFAULT_SORT_KEY)
    limit = int(config.get('profile_memory_limit', DEFAULT_KEY_LIMIT))
    diff_order = config.get('profile_memory_diff', DEFAULT_DIFF_ORDER)
    unit = config.get('profile_memory_unit', DEFAULT_UNIT)
    unit_formatter = get_unit_formatter(unit)

    # Metrics to send
    metrics = []

    # We're running on a live Agent
    if 'profile_memory' not in config:
        gather_top(metrics, None, snapshot, unit_formatter, sort_by, limit, combine)
        return metrics

    if namespaces:
        # Colons can't be part of Windows file paths
        namespaces = [n.replace(':', '_') for n in namespaces]
        location = os.path.join(config['profile_memory'], *namespaces)
    else:
        location = config['profile_memory']

    if not os.path.isdir(location):
        os.makedirs(location)

    # First, write the prettified snapshot
    snapshot_dir = os.path.join(location, 'snapshots')
    if not os.path.isdir(snapshot_dir):
        os.makedirs(snapshot_dir)

    new_snapshot = os.path.join(snapshot_dir, get_timestamp_filename('snapshot'))
    gather_top(metrics, new_snapshot, snapshot, unit_formatter, sort_by, limit, combine)

    # Then, compute the diff if there was a previous run
    previous_snapshot_dump = os.path.join(location, 'last-snapshot')
    if os.path.isfile(previous_snapshot_dump):
        diff_dir = os.path.join(location, 'diffs')
        if not os.path.isdir(diff_dir):
            os.makedirs(diff_dir)

        previous_snapshot = tracemalloc.Snapshot.load(previous_snapshot_dump)

        # and write it
        new_diff = os.path.join(diff_dir, get_timestamp_filename('diff'))
        gather_diff(metrics, new_diff, snapshot, previous_snapshot, unit_formatter, sort_by, limit, combine, diff_order)

    # Finally, dump the current snapshot for doing a diff on the next run
    snapshot.dump(previous_snapshot_dump)

    return metrics
