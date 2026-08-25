"""GitHub Actions I/O helpers."""
import os
from pathlib import Path


def set_outputs(**kwargs: str) -> None:
    """Write key=value pairs to GITHUB_OUTPUT."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with Path(path).open("a") as f:
            for key, value in kwargs.items():
                f.write(f"{key}={value}\n")


def write_summary(content: str) -> None:
    """Append markdown content to GITHUB_STEP_SUMMARY."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with Path(path).open("a") as f:
            f.write(content + "\n")


def parse_bool_env(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable.

    Accepts 'true'/'1'/'yes' as True and 'false'/'0'/'no' as False (case-insensitive).
    Returns ``default`` when the variable is absent or empty.
    """
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default
