#!/usr/bin/python
"""

Copy this code and do

    import hanging_threads

If a thread is at the same place for SECONDS_FROZEN then the
stacktrace is printed.

When example.py is ran, output is the following:

	Starting the deadlocks monitoring
	Sleep 3 seconds in custom func
	----------     Thread 140536184002304 hangs       ----------
	  File "example.py", line 12, in <module>
		sleep(3)
	  File "example.py", line 6, in sleep
		time.sleep(t)
	Sleep 3 seconds
	----------     Thread 140536184002304 awaked      ----------
	----------     Thread 140536184002304 hangs       ----------
	  File "example.py", line 14, in <module>
		time.sleep(3)
	Sleep 3 seconds
	----------     Thread 140536184002304 awaked      ----------
	----------     Thread 140536184002304 hangs       ----------
	  File "example.py", line 16, in <module>
		time.sleep(3)
	Stopping the deadlocks monitoring
	Sleep 3 seconds
	Sleep 3 seconds
	Exiting


"""

import sys
import threading
import linecache
import time

__version__ = "development"
__author__ = "Nicco Kunzmann"


SECONDS_FROZEN = 10  # seconds
TEST_INTERVAL = 100  # milliseconds


def start_monitoring(seconds_frozen=SECONDS_FROZEN,
                     test_interval=TEST_INTERVAL):
    """Start monitoring for hanging threads.

    seconds_frozen - How much time should thread hang to activate
    printing stack trace - default(10)

    tests_interval - Sleep time of monitoring thread (in milliseconds)
    - default(100)
    """

    thread = StoppableThread(target=monitor, args=(seconds_frozen,
                                                   test_interval))
    thread.daemon = True
    thread.start()
    return thread


class StoppableThread(threading.Thread):
    """Thread class with a stop() method.

    The thread itself has to check regularly for the is_stopped()
    condition.
    """
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stopped = False

    def stop(self):
        self._stopped = True

    def is_stopped(self):
        return self._stopped


def monitor(seconds_frozen, test_interval):
    """Monitoring thread function.

    Checks if thread is hanging for time defined by
    ``seconds_frozen`` parameter every ``test_interval`` milliseconds.
    """
    current_thread = threading.current_thread()
    hanging_threads = set()
    old_threads = {}  # Threads found on previous iteration.

    while not current_thread.is_stopped():
        new_threads = get_current_frames()

        # Report died threads.
        for thread_id, thread_data in old_threads.items():
            if thread_id not in new_threads and thread_id in hanging_threads:
                log_died_thread(thread_data)

        # Process live threads.
        time.sleep(test_interval/1000.)
        now = time.time()
        then = now - seconds_frozen
        for thread_id, thread_data in new_threads.items():
            # Don't report the monitor thread.
            if thread_id == current_thread.ident:
                continue
            frame = thread_data['frame']
            # If thread is new or it's stack is changed then update time.
            if (thread_id not in old_threads or
                    frame != old_threads[thread_id]['frame']):
                thread_data['time'] = now
                # If the thread was hanging then report awaked thread.
                if thread_id in hanging_threads:
                    hanging_threads.remove(thread_id)
                    log_awaked_thread(thread_data)
            else:
                # If stack is not changed then keep old time.
                last_change_time = old_threads[thread_id]['time']
                thread_data['time'] = last_change_time
                # Check if this is a new hanging thread.
                if (thread_id not in hanging_threads and
                        last_change_time < then):
                    # Gotcha!
                    hanging_threads.add(thread_id)
                    # Report the hanged thread.
                    log_hanged_thread(thread_data, frame)
        old_threads = new_threads


def get_current_frames():
    """Return current threads prepared for
    further processing.
    """
    threads = {thread.ident: thread for thread in threading.enumerate()}
    return dict(
        (thread_id, {
            'frame': thread2list(frame),
            'time': None,
            'id': thread_id,
            'name': threads[thread_id].name,
            'object': threads[thread_id]
        })
        for thread_id, frame in sys._current_frames().items()
    )


def frame2string(frame):
    """Return info about frame.

    Keyword arg:
        frame

    Return string in format:

    File {file name}, line {line number}, in
    {name of parent of code object} {newline}
    Line from file at line number
    """

    lineno = frame.f_lineno  # or f_lasti
    co = frame.f_code
    filename = co.co_filename
    name = co.co_name
    s = '\tFile "{0}", line {1}, in {2}'.format(filename, lineno, name)
    line = linecache.getline(filename, lineno, frame.f_globals).lstrip()
    return s + '\n\t\t' + line


def thread2list(frame):
    """Return list with string frame representation of each frame of
    thread.
    """
    l = []
    while frame:
        l.insert(0, frame2string(frame))
        frame = frame.f_back
    return l


def threadcaption(thread_data):
    return 'Thread {id} "{name}"'.format(**thread_data)

def log_hanged_thread(thread_data, frame):
    """Print the stack trace of the deadlock after hanging
    `seconds_frozen`.
    """
    write_log('{0} hangs '.format(threadcaption(thread_data)), ''.join(frame))


def log_awaked_thread(thread_data):
    """Print message about awaked thread that was considered as
    hanging.
    """
    write_log('{0} awaked'.format(threadcaption(thread_data)))


def log_died_thread(thread_data):
    """Print message about died thread that was considered as
    hanging.
    """
    write_log('{0} died  '.format(threadcaption(thread_data)))


def write_log(title, message=''):
    """Write formatted log message to stderr."""

    sys.stderr.write(''.join([
        title.center(40).center(60, '-'), '\n', message
    ]))