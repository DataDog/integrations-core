import os
import subprocess
import sys
from contextlib import contextmanager
from io import open

HERE = os.path.dirname(os.path.abspath(__file__))


@contextmanager
def chdir(d, cwd=None):
    origin = cwd or os.getcwd()
    os.chdir(d)

    try:
        yield
    finally:
        os.chdir(origin)


def ensure_reqs_declared(reqs_txt, reqs_in):
    if os.path.isfile(reqs_txt) and not os.path.isfile(reqs_in):
        declacred_lines = []

        with open(reqs_txt, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.split('--hash')[0].strip('\r\n \\')
            if line and not line.startswith('#'):
                declacred_lines.append(line + '\n')

        with open(reqs_in, 'w', encoding='utf-8') as f:
            f.writelines(declacred_lines)


def main():
    args = sys.argv[1:]
    if '--help' in args:
        print('You must specify deps like `upgrage-dep.py requests 2.18.4`.')
        sys.exit()

    verbose = '-v' in args
    if verbose:
        args.remove('-v')

    if len(args) < 2:
        print('You must specify deps like `upgrage-dep.py requests 2.18.4`.')
        sys.exit(1)

    package, version = args[:2]

    for path in os.listdir(HERE):
        check_dir = os.path.join(HERE, path)
        reqs_in = os.path.join(check_dir, 'requirements.in')
        reqs_txt = os.path.join(check_dir, 'requirements.txt')

        ensure_reqs_declared(reqs_txt, reqs_in)

        if os.path.isfile(reqs_in):
            with open(reqs_in, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                try:
                    pkg = line.split('=')[0].strip()
                    if pkg == package:
                        break
                except IndexError:
                    continue
            else:
                continue

            print(repr(lines[i]), pkg, reqs_in)


if __name__ == '__main__':
    main()












