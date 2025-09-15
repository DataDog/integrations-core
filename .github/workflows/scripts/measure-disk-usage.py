import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def get_run_id(commit, workflow):
    print(f"Getting run id for commit: {commit}, workflow: {workflow}")
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
                '--json',
                'databaseId',
                '--jq',
                '.[-1].databaseId',
            ],
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or '').strip()
        if stderr:
            print(stderr)
        print("Failed to get run id (exception).")
        return None
    run_id = result.stdout.strip() if result.stdout else None
    print(f"Run id: {run_id}")
    return run_id


def get_dep_sizes_json(current_commit, platform, run_id):
    print(f"Getting dependency sizes json for commit: {current_commit}, platform: {platform}")
    # run_id = get_run_id(current_commit, '.github/workflows/resolve-build-deps.yaml')
    if run_id and check_artifact_exists(run_id, f'target-{platform}'):
        dep_sizes_json = get_current_sizes_json(run_id, platform)
        print(f"Dependency sizes json path: {dep_sizes_json}")
        return dep_sizes_json
    else:
        print("Dependency sizes json not found for current commit.")
        return None


def check_artifact_exists(run_id, artifact_name):
    print(f"Checking if artifact exists: run_id={run_id}, artifact_name={artifact_name}")
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
    print(f"Available artifacts: {artifact_names}")
    if artifact_name not in artifact_names:
        print(f"Artifact '{artifact_name}' not found in run {run_id}")
        return False

    print(f"Found artifact: {artifact_name}")
    return True


def get_current_sizes_json(run_id, platform):
    print(f"Getting current sizes json for run_id={run_id}, platform={platform}")
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Downloading artifacts to {tmpdir}")
        _ = subprocess.run(
            [
                'gh',
                'run',
                'download',
                run_id,
                '--name',
                f'target-{platform}',
                '--dir',
                tmpdir,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Downloaded artifacts to {tmpdir}")
        # Look for the sizes.json file in the downloaded artifacts
        sizes_file = os.path.join(tmpdir, platform, 'py3', 'sizes.json')

        if os.path.exists(sizes_file):
            print(f"Found sizes.json at {sizes_file}")
            dest_path = os.path.join(os.getcwd(), f'{platform}.json')
            shutil.move(sizes_file, dest_path)
            return dest_path
        else:
            print(f"sizes.json not found at {sizes_file}")
            return None


def get_artifact(run_id, artifact_name):
    print(f"Downloading artifact: {artifact_name} from run_id={run_id}")
    _ = subprocess.run(
        [
            'gh',
            'run',
            'download',
            run_id,
            '--name',
            artifact_name,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    artifact_path = os.path.join(os.getcwd(), artifact_name)
    print(f"Artifact downloaded to: {artifact_path}")
    return artifact_path


def get_previous_dep_sizes_json(base_commit, platform):
    print(f"Getting previous dependency sizes json for base_commit={base_commit}, platform={platform}")
    run_id = get_run_id(base_commit, '.github/workflows/measure-disk-usage.yml')
    print(f"Previous run_id: {run_id}")
    compressed_json = None
    uncompressed_json = None
    if run_id and check_artifact_exists(run_id, f'status_compressed_{platform}.json'):
        compressed_json = get_artifact(run_id, f'status_compressed_{platform}.json')
    if run_id and check_artifact_exists(run_id, f'status_uncompressed_{platform}.json'):
        uncompressed_json = get_artifact(run_id, f'status_uncompressed_{platform}.json')
    print(f"Compressed json: {compressed_json}")
    print(f"Uncompressed json: {uncompressed_json}")
    sizes_json = parse_sizes_json(compressed_json, uncompressed_json)
    output_path = f'{platform}.json'
    with open(output_path, 'w') as f:
        json.dump(sizes_json, f, indent=2)
    print(f"Wrote merged sizes json to {output_path}")
    return output_path


def parse_sizes_json(compressed_json_path, uncompressed_json_path):
    with open(compressed_json_path, 'r') as f:
        compressed_list = list(json.load(f))
    with open(uncompressed_json_path, 'r') as f:
        uncompressed_list = list(json.load(f))

    sizes_json = {
        dep["Name"]: {
            "compressed": int(dep["Size_Bytes"]),
            "version": dep.get("Version"),
        }
        for dep in compressed_list
    }

    for dep in uncompressed_list:
        name = dep["Name"]
        entry = sizes_json.setdefault(name, {"version": dep.get("Version")})
        entry["uncompressed"] = int(dep["Size_Bytes"])

    return sizes_json


def main():
    parser = argparse.ArgumentParser(description='Calculate the current repo size')
    parser.add_argument('--current-commit', required=True, help='Current commit sha')
    parser.add_argument('--base-commit', required=True, help='Base commit hash')
    parser.add_argument('--platform', required=True, help='Platform to compare')
    parser.add_argument('--to-dd-key', required=False, help='Send to Datadog')
    parser.add_argument('--run-id', required=False, help='Run id')
    args = parser.parse_args()

    dep_sizes_json = get_dep_sizes_json(args.current_commit, args.platform, args.run_id)
    if not dep_sizes_json:
        dep_sizes_json = get_previous_dep_sizes_json(args.base_commit, args.platform)

    command_args = [
        "ddev",
        "size",
        "status",
        "--platform",
        args.platform,
        "--dependency-sizes",
        dep_sizes_json,
        "--format",
        "json",
    ]
    if args.to_dd_key:
        command_args += ["--to-dd-key", args.to_dd_key]

    print(f"Running command: {' '.join(command_args)}")
    subprocess.run(command_args, check=True)

    command_args_compressed = command_args + ["--compressed"]
    print(f"Running command: {' '.join(command_args_compressed)}")
    subprocess.run(command_args_compressed, check=True)

    return 0


if __name__ == '__main__':
    sys.exit(main())
