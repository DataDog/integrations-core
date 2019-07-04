import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) == 1:
        return

    checks = sys.argv[1].strip()
    print(f'Checks chosen: {checks}')

    if checks == 'changed':
        print('Detecting changed checks...')
        result = subprocess.run(['ddev', 'test', '--list'], encoding='utf-8', capture_output=True, check=True)
        checks = sorted(c.strip('`') for c in re.findall('^`[^`]+`', result.stdout, re.M))
    else:
        checks = sorted(c for c in checks.split() if c and not c.startswith('-'))

    for check in checks:
        scripts_path = os.path.join(HERE, check)
        if not os.path.isdir(scripts_path):
            continue

        print(f'Setting up: {check}')

        scripts = sorted(os.listdir(scripts_path))
        for script in scripts:
            script_file = os.path.join(scripts_path, script)
            display_header = f'Running: {script_file}'
            print(f'\n{display_header}\n{"-" * len(display_header)}\n')

            # Sometimes the scripts output before our header
            time.sleep(10)

            subprocess.run([script_file], shell=True, check=True)


if __name__ == '__main__':
    main()
