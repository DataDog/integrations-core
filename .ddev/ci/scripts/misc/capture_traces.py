# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--port', required=True)
    parser.add_argument('--record', required=True)
    parser.add_argument('--watch', required=True)
    args = parser.parse_args()

    process = subprocess.Popen(['httpr', '-port', args.port, '-record', args.record])
    while True:
        if os.path.isfile(args.watch):
            if sys.platform == 'win32':
                from ctypes import windll

                assert windll.kernel32.FreeConsole()
                assert windll.kernel32.AttachConsole(process.pid)
                print('foo')
                os.kill(process.pid, signal.CTRL_C_EVENT)
                print('bar')
            else:
                os.kill(process.pid, signal.SIGINT)

            break

        time.sleep(0.1)


if __name__ == '__main__':
    main()
