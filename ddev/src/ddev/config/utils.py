import tomlkit
from tomlkit.toml_document import TOMLDocument

from ddev.utils.fs import Path


def save_toml_document(document: TOMLDocument, path: Path):
    path.ensure_parent_dir_exists()
    path.write_atomic(tomlkit.dumps(document), 'w', encoding='utf-8')


def create_toml_document(config: dict) -> TOMLDocument:
    return tomlkit.item(config)
