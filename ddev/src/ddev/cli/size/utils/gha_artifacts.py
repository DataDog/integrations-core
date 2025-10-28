from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from ddev.cli.application import Application
from ddev.cli.size.utils.size_model import Size, Sizes
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.size.utils.common_funcs import DependencyEntry

RESOLVE_BUILD_DEPS_WORKFLOW = '.github/workflows/resolve-build-deps.yaml'
MEASURE_DISK_USAGE_WORKFLOW = '.github/workflows/measure-disk-usage.yml'


def get_dependencies_from_artifact(
    dependency_sizes: dict[str, DependencyEntry], platform: str, py_version: str, compressed: bool
) -> Sizes:
    return Sizes(
        [
            Size(
                name=name,
                version=entry.get("version", ""),
                size_bytes=int(entry.get("compressed", 0) if compressed else entry.get("uncompressed", 0)),
                type="Dependency",
                platform=platform,
                python_version=py_version,
            )
            for name, entry in dependency_sizes.items()
        ]
    )


def artifact_exists(app: Application, commit: str, artifact_name: str, workflow: str) -> bool:
    import subprocess

    run_id = get_run_id_by_commit(app, commit, workflow)
    if not run_id:
        return False
    result = subprocess.run(
        [
            'gh',
            'api',
            f'repos/DataDog/integrations-core/actions/runs/{run_id}/artifacts',
            '--jq',
            f'.artifacts[] | select(.name == "{artifact_name}")',
        ],
        capture_output=True,
    )
    return bool(result.stdout.decode('utf-8').strip())


@cache
def get_previous_commit(app: Application, commit: str) -> str:
    try:
        commits = app.repo.git.log(["hash:%H"], n=2, source="origin/master")
        app.display_debug(f"Last two commits on master: {commits}")
        if commits[0]["hash"] != commit:
            app.display_debug(f"Found last commit on master: {commits[0]['hash']}")
            return commits[0]["hash"]
        else:
            app.display_debug("Currently in master, using previous commit")
            return commits[1]["hash"]
    except Exception as e:
        if e and "Not a valid commit name" in str(e):
            app.display_error("No previous commit found")
        else:
            app.display_error(f"Failed to get previous commit: {e}")
        return ""


def get_dep_sizes(app: Application, current_commit: str, platform: str, py_version: str, compressed: bool) -> Sizes:
    """
    Gets the dependency sizes json for a given commit and platform when dependencies were resolved.
    """
    import json

    run_id = get_run_id_by_commit(app, current_commit, RESOLVE_BUILD_DEPS_WORKFLOW)
    if run_id:
        dep_sizes_json_path = get_current_sizes_json(app, run_id, platform, py_version)
        if dep_sizes_json_path:
            dependency_sizes = json.loads(dep_sizes_json_path.read_text())
            return get_dependencies_from_artifact(dependency_sizes, platform, py_version, compressed)

    return Sizes([])


@cache
def get_run_id_by_commit(app: Application, commit: str, workflow: str) -> str | None:
    import subprocess

    app.display_debug(f"Fetching workflow run ID for {commit=} ({workflow.split('/')[-1]})")

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

    run_id = result.stdout.strip() if result.stdout else None
    if run_id:
        app.display_debug(f"Workflow run ID: {run_id}")
    else:
        app.display_error(f"No workflow run found for {commit} ({workflow.split('/')[-1]})")

    return run_id


@cache
def get_last_run_id_by_branch(app: Application, branch: str, workflow: str) -> tuple[str | None, str | None]:
    import json
    import subprocess

    app.display_debug(f"Fetching last workflow run ID for {branch} ({workflow.split('/')[-1]})")

    try:
        result = subprocess.run(
            [
                'gh',
                'run',
                'list',
                '--workflow',
                workflow,
                '--branch',
                branch,
                '--json',
                'databaseId,status,headSha',
            ],
            capture_output=True,
            text=True,
        )
    except Exception as e:
        app.display_error(f"Failed to get last workflow run ID for {branch} ({workflow.split('/')[-1]}): {e}")
        return None, None

    runs = json.loads(result.stdout)
    for run in runs:
        if run['status'] == 'completed':
            app.display_debug(f"Found completed run {run['databaseId']} in commit {run['headSha']}")
            return str(run['databaseId']), run['headSha']
    return None, None


def get_current_sizes_json(app: Application, run_id: str, platform: str, py_version: str) -> Path | None:
    '''
    Downloads the dependency sizes json for a given run id and platform when dependencies were resolved.
    '''
    import subprocess
    import tempfile

    app.display(f"Retrieving dependency sizes artifact ({run_id=}, {platform=})")
    with tempfile.TemporaryDirectory() as tmpdir:
        app.display_debug(f"Downloading artifacts to {tmpdir}...")
        try:
            subprocess.run(
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
        except subprocess.CalledProcessError as e:
            if e.stderr and "no valid artifacts found" in e.stderr:
                app.display_error(f"No resolved dependencies found for {platform=} ({run_id=})")
            else:
                app.display_error(f"Failed to download dependency sizes ({run_id=}, {platform=}): {e}")
                app.display_warning(e.stderr)

            return None

        app.display_debug("Artifact extraction complete")
        sizes_file = Path(tmpdir) / platform / 'py3' / 'sizes.json'

        if not sizes_file.is_file():
            app.display_warning(f"Dependency sizes artifact missing: {sizes_file.name}")
            return None

        app.display_debug(f"Found dependency sizes: {sizes_file.name}")
        dest_path = sizes_file.rename(f"{platform}_{py_version}.json")
        return dest_path


@cache
def get_artifact(app: Application, run_id: str, artifact_name: str, target_dir: str | None = None) -> Path | None:
    import subprocess

    try:
        cmd = [
            'gh',
            'run',
            'download',
            run_id,
            '--name',
            artifact_name,
        ]
        if target_dir:
            cmd.extend(['--dir', target_dir])

        subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        app.display_warning(f"Failed to download artifact '{artifact_name}' ({run_id=}): {e}")
        app.display_warning(e.stderr)
        return None

    artifact_path = Path(target_dir) / artifact_name if target_dir else Path(artifact_name)
    app.display_debug(f"Saved to {artifact_path}")
    return artifact_path


@cache
def get_status_sizes(
    app: Application,
    compressed: bool,
    commit: str | None = None,
    branch: str | None = None,
) -> tuple[Sizes, str]:
    import json
    import tempfile

    '''
    Gets the sizes json for a given commit or for the latest run on a branch from the measure disk usage workflow.
    If a branch is provided, it retrieves the most recent run for that branch.
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
        if commit:
            run_id = get_run_id_by_commit(app, commit, MEASURE_DISK_USAGE_WORKFLOW)
        elif branch:
            run_id, commit = get_last_run_id_by_branch(app, branch, MEASURE_DISK_USAGE_WORKFLOW)
        else:
            app.display_error("No commit or branch provided")
            return Sizes([]), ""

        if run_id is None or commit is None:
            return Sizes([]), ""

        artifact_name = 'status_compressed.json' if compressed else 'status_uncompressed.json'
        sizes_json = get_artifact(app, run_id, artifact_name, tmpdir)
        if not sizes_json:
            app.display_error(f"No dependency sizes found in {commit=}\n")
            return Sizes([]), ""

        sizes_list = list(json.loads(sizes_json.read_text()))
        return Sizes([Size(**size) for size in sizes_list]), commit
