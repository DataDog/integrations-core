import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import json


def get_run_id(commit, workflow):
    try:
        result = subprocess.run(
            [
                'gh',
                'run',
                'list',
                '--workflow',
                workflow,
                '-c',
                commit,
                '--status',
                'completed',
                '--json',
                'databaseId',
                '--jq',
                '.[-1].databaseId',
            ],
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or '').strip()
        if stderr:
            print(stderr)
        return None
    return result.stdout.strip()

def get_dep_sizes_json(current_commit, platform):
    run_id = get_run_id(current_commit, '.github/workflows/resolve-build-deps.yaml')
    if run_id and check_artifact_exists(run_id, f'target-{platform}'):
        dep_sizes_json = get_current_sizes_json(run_id, platform)
        return dep_sizes_json
    else:
        return None


def check_artifact_exists(run_id, artifact_name):
    result = subprocess.run(
            [
                'gh',
                'api',
                f'repos/Datadog/integrations-core/actions/runs/{run_id}/artifacts',
                '--jq',
                '.artifacts[].name',
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    artifact_names = {n.strip() for n in (result.stdout or '').splitlines() if n.strip()}
    if artifact_name not in artifact_names:
        print(f"Artifact '{artifact_name}' not found in run {run_id}")
        return False

    print(f"Found artifact: {artifact_name}")
    return True

def get_current_sizes_json(run_id, platform):
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Downloading artifacts to {tmpdir}")
        _ = subprocess.run(
            ['gh', 'run', 'download', run_id, '--name', f'target-{platform}', '--dir', tmpdir],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Downloaded artifacts to {tmpdir}")
        # Look for the sizes.json file in the downloaded artifacts
        sizes_file = os.path.join(tmpdir, platform, 'py3', 'sizes.json')

        if os.path.exists(sizes_file):
            print(f"Found sizes.json at {sizes_file}")
            shutil.move(sizes_file, os.path.join(os.getcwd(), f'{platform}.json'))
            return os.getcwd() / f'{platform}.json'
        else:
            print(f"sizes.json not found at {sizes_file}")
            return None

def get_artifact(run_id, artifact_name):
    _ = subprocess.run(
        ['gh', 'run', 'download', run_id, '--name', artifact_name],
        check=True,
        capture_output=True,
        text=True,
    )
    return os.path.join(os.getcwd(), artifact_name)

def get_previous_dep_sizes_json(base_commit, platform):
    # Get the previous commit in master branch
    result = subprocess.run(
        ['git', 'rev-parse', f'{base_commit}~1'],
        check=True,
        capture_output=True,
        text=True,
    )
    prev_commit = result.stdout.strip()
    run_id = get_run_id(prev_commit, '.github/workflows/measure-disk-usage.yml')
    if run_id and check_artifact_exists(run_id, f'status_uncompressed_{platform}.json'):
        uncompressed_json = get_artifact(run_id, f'status_uncompressed_{platform}.json')
    if run_id and check_artifact_exists(run_id, f'status_compressed_{platform}.json'):
        compressed_json = get_artifact(run_id, f'status_compressed_{platform}.json')

    sizes_json = parse_sizes_json(compressed_json, uncompressed_json)
    with open(f'{platform}.json', 'w') as f:
        json.dump(sizes_json, f, indent=2)
    return f'{platform}.json'


def parse_sizes_json(compressed_json_path, uncompressed_json_path):
    with open(compressed_json_path, 'r') as f:
        compressed_list = json.load(f)
    with open(uncompressed_json_path, 'r') as f:
        uncompressed_list = json.load(f)

    sizes_json = {
        dep["Name"]: {
            "compressed": dep["Size_Bytes"],
            "version": dep["Version"]
        }
        for dep in compressed_list
    }

    for dep in uncompressed_list:
        sizes_json[dep["Name"]]["uncompressed"] = dep["Size_Bytes"]
 
    return sizes_json


def main():
    parser = argparse.ArgumentParser(description='Calculate the current repo size')
    parser.add_argument('--current-commit', required=True, help='Current commit hash')
    parser.add_argument('--base-commit', required=True, help='Base commit hash')
    parser.add_argument('--platform', required=True, help='Platform to compare')
    parser.add_argument('--to-dd-key', required=False, help='Send to Datadog')
    args = parser.parse_args()

    dep_sizes_json = get_dep_sizes_json(args.current_commit, args.platform)
    if not dep_sizes_json:
        dep_sizes_json = get_previous_dep_sizes_json(args.base_commit, args.platform)

    command = (
        f"ddev size status "
        f"--platform {args.platform} "
        f"--dependency-sizes {dep_sizes_json} "
        f"--format json"
    )
    if args.send_to_dd:
        command += f" --to-dd-key {args.send_to_dd}"

    subprocess.run(command, check=True)

    command += "--compressed"

    subprocess.run(command, check=True)

    return 0




if __name__ == '__main__':
    sys.exit(main())
