#!/usr/bin/env bash

# Requires python 3.11+ (for tomllib) and the `build` package.
# Run this script from the root of the repo.
# The TL;DR of this script is: for every subdirectory with a pyproject.toml file we build an empty Python wheel.

mkdir -p dist
mkdir -p pkg_placeholder
for file_or_subdir in *; do
    if [[ -d "${file_or_subdir}" ]]; then
        pyproject="${file_or_subdir}/pyproject.toml"
        if [[ -f "${pyproject}" ]]; then
            pypi_pkg_name=$(python -c "import tomllib, pathlib; contents = pathlib.Path('${pyproject}').read_text(); data = tomllib.loads(contents); print(data['project']['name'])")
            # multiline strings are sensitive to indentation, so we must unindent the following command
cat <<EOF > pkg_placeholder/pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[project]
name = "${pypi_pkg_name}"
version = "0.0.1"
[tool.hatch.build.targets.wheel]
bypass-selection = true
EOF
            # We only want wheels.
            # We don't need build isolation because we'll trash the env anyway in CI.
            # Skipping isolation speeds up the job.
            python -m build --no-isolation --wheel pkg_placeholder
            mv pkg_placeholder/dist/* dist/
        fi
    fi
done
