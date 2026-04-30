import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "build_queue", ROOT / "scripts" / "build_queue.py"
)
build_queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_queue)


def test_normalize_strips_quotes_and_spaces():
    assert build_queue.normalize("Redis ") == "redis"
    assert build_queue.normalize("SQL Server") == "sql_server"
    assert build_queue.normalize(".net clr") == "net_clr"
    assert build_queue.normalize("nginx-ingress-controller") == "nginx_ingress_controller"


def test_resolve_directory_for_known_aliases(tmp_path, monkeypatch):
    (tmp_path / "redisdb" / "assets" / "configuration").mkdir(parents=True)
    (tmp_path / "redisdb" / "assets" / "configuration" / "spec.yaml").write_text("x")
    monkeypatch.chdir(tmp_path)
    assert build_queue.resolve_directory("redis") == "redisdb"


def test_resolve_directory_returns_none_when_no_spec(tmp_path, monkeypatch):
    (tmp_path / "logs").mkdir()
    monkeypatch.chdir(tmp_path)
    assert build_queue.resolve_directory("logs") is None


def test_resolve_directory_uses_normalized_name_when_no_alias(tmp_path, monkeypatch):
    (tmp_path / "haproxy" / "assets" / "configuration").mkdir(parents=True)
    (tmp_path / "haproxy" / "assets" / "configuration" / "spec.yaml").write_text("x")
    monkeypatch.chdir(tmp_path)
    assert build_queue.resolve_directory("haproxy") == "haproxy"
