import json
import os
import subprocess
import tempfile
from functools import cache
from typing import Literal, overload

from ddev.cli.application import Application
from ddev.cli.size.utils.models import DependencyEntry, FileDataEntry
from ddev.utils.fs import Path

RESOLVE_BUILD_DEPS_WORKFLOW = '.github/workflows/resolve-build-deps.yaml'
MEASURE_DISK_USAGE_WORKFLOW = '.github/workflows/measure-disk-usage.yml'


@cache
def get_last_dependency_sizes_artifact(
    app: Application, commit: str, platform: str, py_version: str, compressed: bool
) -> Path | None:
    '''
    Lockfiles of dependencies are not updated in the same commit as the dependencies are updated.
    So in each commit, there is an artifact with the sizes of the wheels that were built to get the actual
    size of that commit.
    '''
    size_type = 'compressed' if compressed else 'uncompressed'
    app.display(f"Retrieving dependency sizes for {commit} ({platform}, py{py_version}, {size_type})")

    dep_sizes_json = get_dep_sizes_json(app, commit, platform, py_version)
    if not dep_sizes_json:
        app.display_debug("No dependency sizes in current commit, searching ancestors")
        previous_commit = get_previous_commit(app, commit)
        app.display(f"\n -> Searching for dependency sizes in previous commit: {previous_commit}")
        if not previous_commit:
            return None
        dep_sizes_json = get_status_sizes_from_commit(
            app, previous_commit, platform, py_version, compressed, file=True, only_dependencies=True
        )
    return Path(dep_sizes_json) if dep_sizes_json else None


@cache
def get_previous_commit(app: Application, commit: str) -> str | None:
    try:
        base_commit = app.repo.git.merge_base(commit, "origin/master")
        if base_commit != commit:
            app.display_debug(f"Found base commit: {base_commit}")
            return base_commit
        else:
            app.display_debug("No base commit found, using previous commit")
            return app.repo.git.log(["hash:%H"], n=2, source=commit)[1]["hash"]
    except Exception as e:
        if e and "Not a valid commit name" in str(e):
            app.display_error("No previous commit found")
        else:
            app.display_error(f"Failed to get previous commit: {e}")
        return None


@cache
def get_dep_sizes_json(app: Application, current_commit: str, platform: str, py_version: str) -> Path | None:
    '''
    Gets the dependency sizes json for a given commit and platform when dependencies were resolved.
    '''
    app.display(f"\n -> Checking if dependency sizes were resolved in commit: {current_commit}")

    run_id = get_run_id(app, current_commit, RESOLVE_BUILD_DEPS_WORKFLOW)
    if run_id:
        dep_sizes_json = get_current_sizes_json(app, run_id, platform, py_version)
        return dep_sizes_json
    else:
        return None


@cache
def get_run_id(app: Application, commit: str, workflow: str) -> str | None:
    app.display_debug(f"Fetching workflow run ID for {commit} ({os.path.basename(workflow)})")

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
        app.display_error(f"No workflow run found for {commit} ({os.path.basename(workflow)})")

    return run_id


@cache
def get_current_sizes_json(app: Application, run_id: str, platform: str, py_version: str) -> Path | None:
    '''
    Downloads the dependency sizes json for a given run id and platform when dependencies were resolved.
    '''
    app.display(f"Retrieving dependency sizes artifact (run={run_id}, platform={platform})")
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
                app.display_warning(f"No resolved dependencies found for platform {platform} (run {run_id})")
            else:
                app.display_error(f"Failed to download dependency sizes (run={run_id}, platform={platform}): {e}")
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
    app.display(f"Downloading artifact '{artifact_name}' (run {run_id})...")
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
        app.display_warning(f"Failed to download artifact '{artifact_name}' (run {run_id}): {e}")
        app.display_warning(e.stderr)
        return None

    artifact_path = Path(target_dir) / artifact_name if target_dir else Path(artifact_name)
    app.display_debug(f"Saved to {artifact_path}")
    return artifact_path


@overload
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: Literal[True],
    only_dependencies: bool,
) -> Path | None: ...


@overload
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: Literal[False],
    only_dependencies: Literal[False],
) -> list[FileDataEntry]: ...


@overload
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: Literal[False],
    only_dependencies: Literal[True],
) -> dict[str, DependencyEntry]: ...


@cache
def get_status_sizes_from_commit(
    app: Application,
    commit: str,
    platform: str,
    py_version: str,
    compressed: bool,
    file: bool = False,
    only_dependencies: bool = False,
) -> list[FileDataEntry] | dict[str, DependencyEntry] | Path | None:
    '''
    Gets the sizes json for a given commit from the measure disk usage workflow.
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
        if (run_id := get_run_id(app, commit, MEASURE_DISK_USAGE_WORKFLOW)) is None:
            return []

        artifact_name = 'status_compressed.json' if compressed else 'status_uncompressed.json'
        sizes_json = get_artifact(app, run_id, artifact_name, tmpdir)

        if not sizes_json:
            app.display_error(f"No dependency sizes found for {platform} py{py_version} in commit {commit}\n")
            return []

        sizes: list[FileDataEntry] | dict[str, DependencyEntry]
        if only_dependencies:
            sizes = parse_dep_sizes_json(sizes_json, platform, py_version, compressed)
        else:
            sizes = filter_sizes_json(sizes_json, platform, py_version)

        if file and sizes:
            target_path = f"{platform}_{py_version}.json"
            with open(target_path, "w") as f:
                json.dump(sizes, f, indent=2)
            return Path(target_path)
        elif file and not sizes:
            return None
        else:
            return sizes


def filter_sizes_json(sizes_json: Path, platform: str, py_version: str) -> list[FileDataEntry]:
    '''
    Filters the sizes json for a given platform and python version.
    '''
    sizes_list: list[FileDataEntry] = list(json.loads(sizes_json.read_text()))
    return [size for size in sizes_list if size["Platform"] == platform and size["Python_Version"] == py_version]


@cache
def parse_dep_sizes_json(
    sizes_json_path: Path,
    platform: str,
    py_version: str,
    compressed: bool,
) -> dict[str, DependencyEntry]:
    '''
    Parses the dependency sizes json for a given platform and python version.
    '''
    sizes_list = list(json.loads(sizes_json_path.read_text()))
    sizes: dict[str, DependencyEntry] = {}
    for dep in sizes_list:
        if (
            dep.get("Type") == "Dependency"
            and dep.get("Platform") == platform
            and dep.get("Python_Version") == py_version
        ):
            name = dep["Name"]
            entry: DependencyEntry = {"version": dep.get("Version", "")}
            if compressed:
                entry["compressed"] = int(dep["Size_Bytes"])
            else:
                entry["uncompressed"] = int(dep["Size_Bytes"])
            sizes[name] = entry
    return sizes
