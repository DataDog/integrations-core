# datadog_hatch_wrapper/build.py
from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional


# PEP 517 functions
def get_requires_for_build_wheel(config_settings=None):
    # We need hatchling (the real backend) + wheel tools for repacking + pathspec/tomllib
    return ["hatchling", "wheel", "pathspec"]


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    # delegate to hatchling if available
    try:
        from hatchling.build import prepare_metadata_for_build_wheel as _pmd
    except Exception:
        raise
    return _pmd(metadata_directory, config_settings=config_settings)


def build_wheel(
    wheel_directory: str, config_settings: Optional[dict] = None, metadata_directory: Optional[str] = None
) -> str:
    """
    Build the wheel using hatchling into a temporary directory, post-process it (remove tests),
    then move the final wheel into `wheel_directory` and return the filename.
    """

    from wheel.cli.pack import pack
    from wheel.cli.unpack import unpack

    # 1) use hatchling to build wheel(s) into a temp dir
    tmpd = TemporaryDirectory()
    tmp_path = Path(tmpd.name)
    try:
        # call hatchling's build_wheel; its signature matches PEP 517:
        from hatchling.build import build_wheel as hatch_build_wheel

        hatch_build_wheel(str(tmp_path), config_settings=config_settings)
    except Exception:
        tmpd.cleanup()
        raise

    # 2) find the built wheel
    wheels = list(tmp_path.glob("*.whl"))
    if not wheels:
        tmpd.cleanup()
        raise RuntimeError("hatchling did not produce a wheel")

    # If there is more than one, choose the one you expect (or iterate)
    wheel_path = wheels[0]

    # 3) strip tests using same logic as in your PR:
    #    - check against files_to_remove.toml or a spec
    def _load_excluded_spec():
        import tomllib

        import pathspec

        cfg = Path(__file__).parent / "files_to_remove.toml"
        with cfg.open("rb") as f:
            data = tomllib.load(f)
        patterns = data.get("excluded_paths", [])
        return pathspec.PathSpec.from_lines("gitignore", patterns)

    def _is_excluded(member: str) -> bool:
        spec = _load_excluded_spec()
        rel = Path(member).as_posix()
        return spec.match_file(rel) or spec.match_file(rel + "/")

    # quick check: does wheel contain excluded entries?
    from zipfile import ZipFile

    with ZipFile(wheel_path, "r") as zf:
        if not any(_is_excluded(name) for name in zf.namelist()):
            # nothing to do; just move the wheel to final dir
            final = Path(wheel_directory) / wheel_path.name
            shutil.move(str(wheel_path), str(final))
            tmpd.cleanup()
            return final.name

    # Unpack, remove excluded files/directories, repack
    tmp_unpack = TemporaryDirectory()
    try:
        unpack(wheel_path, dest=tmp_unpack)
        unpacked_dir = next(Path(tmp_unpack.name).iterdir())

        # walk bottom-up and remove excluded files/folders
        for root, dirs, files in os.walk(unpacked_dir, topdown=False):
            rootp = Path(root)
            for d in list(dirs):
                full_dir = rootp / d
                rel = full_dir.relative_to(unpacked_dir).as_posix()
                if _is_excluded(rel):
                    shutil.rmtree(full_dir)
                    dirs.remove(d)
            for f in files:
                rel = (rootp / f).relative_to(unpacked_dir).as_posix()
                if _is_excluded(rel):
                    (rootp / f).unlink()

        # repack into wheel_directory (pack writes a new wheel file)
        pack(unpacked_dir, dest_dir=wheel_directory)

        # pack puts a new wheel file in wheel_directory; pick the freshest one
        # and return its filename
        final_wheels = sorted(Path(wheel_directory).glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not final_wheels:
            raise RuntimeError("Failed to repack wheel")
        final = final_wheels[0]
        return final.name
    finally:
        tmpd.cleanup()
        try:
            tmp_unpack and shutil.rmtree(tmp_unpack.name)
        except Exception:
            pass
