# import inspect
# import shutil
# import sys
# import tomllib
# import zipfile
# from functools import cache
# from pathlib import Path

# import pathspec
# from setuptools import build_meta as _orig


# def remove_test_files(wheel_path: Path) -> None:
#     """
#     Remove excluded files and directories from a built wheel.
#     Prints the number of files removed.
#     """
#     tmp_wheel = wheel_path.with_suffix(".tmp.whl")
#     removed_count = 0

#     with (
#         zipfile.ZipFile(wheel_path, "r") as zin,
#         zipfile.ZipFile(tmp_wheel, "w", compression=zipfile.ZIP_DEFLATED) as zout,
#     ):
#         for info in zin.infolist():
#             rel = info.filename
#             if is_excluded_from_wheel(rel):
#                 removed_count += 1
#                 continue  # skip excluded file or directory

#             data = zin.read(rel)
#             zout.writestr(info, data)

#     shutil.move(tmp_wheel, wheel_path)
#     print(f"Removed {removed_count} files from {wheel_path.name}")


# def is_excluded_from_wheel(path: str | Path) -> bool:
#     """
#     Return True if `path` (file or directory) should be excluded per files_to_remove.toml.
#     Matches:
#       - type annotation files: **/*.pyi, **/py.typed
#       - test directories listed with a trailing '/'
#     """
#     spec = _load_excluded_spec()
#     rel = Path(path).as_posix()

#     if spec.match_file(rel) or spec.match_file(rel + "/"):
#         return True

#     return False


# @cache
# def _load_excluded_spec() -> pathspec.PathSpec:
#     """
#     Load excluded paths from files_to_remove.toml and compile them
#     with .gitignore-style semantics.
#     """
#     config_path = Path(__file__).parent / "files_to_remove.toml"
#     with open(config_path, "rb") as f:
#         config = tomllib.load(f)

#     patterns = config.get("excluded_paths", [])
#     return pathspec.PathSpec.from_lines("gitignore", patterns)


# def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
#     """Intercept wheel building to strip test files."""
#     wheel_file = _orig.build_wheel(wheel_directory, config_settings, metadata_directory)

#     # Post-process the wheel to remove tests
#     wheel_path = Path(wheel_directory) / wheel_file
#     remove_test_files(wheel_path)

#     return wheel_file


# # Proxy all other PEP 517 hooks
# # prepare_metadata_for_build_wheel = _orig.prepare_metadata_for_build_wheel
# # build_sdist = _orig.build_sdist
# # (better do by iterating over _orig methods instead)
# print("-> Inspecting _orig methods")
# for name, func in inspect.getmembers(_orig, inspect.isfunction):
#     # Only copy methods if they haven't been defined in the current module
#     # (i.e., don't overwrite your custom build_wheel)
#     print("Name: ", name, "Func: ", func, "Is in globals: ", name in globals())
#     if name not in globals():
#         globals()[name] = func
#         print("Added to globals: ", name)

# # for name in dir(_orig):
# #     # Check if the attribute name is a PEP 517 hook and not one we defined/overrode
# #     if name.startswith('build_') or 'requires_for' in name:
# #         if name not in globals():
# #             setattr(sys.modules[__name__], name, getattr(_orig, name))
