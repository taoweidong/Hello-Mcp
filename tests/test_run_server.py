"""统一启动脚本测试"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_server.py"

spec = importlib.util.spec_from_file_location("hello_mcp_run_server", SCRIPT)
assert spec is not None and spec.loader is not None
run_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_server)


def test_usage_lists_all_servers(capsys):
    run_server.print_usage()

    output = capsys.readouterr().out
    for name in run_server.SERVER_MODULES:
        assert name in output
    assert "端口" in output


def test_usage_survives_broken_module(monkeypatch, capsys):
    """回归：新增服务缺可选依赖时，用法列表不应整体崩溃"""
    real_import = run_server.importlib.import_module

    def fake_import(module_path):
        if module_path == run_server.SERVER_MODULES["weather"]:
            raise ImportError("missing optional dependency")
        return real_import(module_path)

    monkeypatch.setattr(run_server.importlib, "import_module", fake_import)

    run_server.print_usage()

    output = capsys.readouterr().out
    assert "weather" in output
    assert "不可用" in output
    assert "qwen" in output


def test_usage_reports_missing_port(monkeypatch, capsys):
    fake_module = ModuleType("fake_server")
    fake_module.__doc__ = "Fake server"
    real_import = run_server.importlib.import_module

    def fake_import(module_path):
        if module_path == "fake.server":
            return fake_module
        return real_import(module_path)

    monkeypatch.setattr(run_server.importlib, "import_module", fake_import)
    monkeypatch.setitem(run_server.SERVER_MODULES, "fake", "fake.server")

    run_server.print_usage()

    assert "不可用" in capsys.readouterr().out


def test_load_server_requires_mcp(monkeypatch):
    monkeypatch.setitem(run_server.SERVER_MODULES, "fake", "tests.test_run_server")

    with pytest.raises(AttributeError, match="未定义 mcp"):
        run_server.load_server("fake")


def test_all_registered_servers_expose_mcp_and_port():
    for name in run_server.SERVER_MODULES:
        module = run_server.load_server(name)
        assert hasattr(module, "mcp")
        assert isinstance(module.PORT, int)


def test_main_without_args_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_server.py"])

    with pytest.raises(SystemExit) as excinfo:
        run_server.main()

    assert excinfo.value.code == 1


def test_main_rejects_unknown_server(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_server.py", "nope"])

    with pytest.raises(SystemExit) as excinfo:
        run_server.main()

    assert excinfo.value.code == 1


def test_main_reports_load_error(monkeypatch, capsys):
    def fail(name):
        raise ImportError("boom")

    monkeypatch.setattr(run_server, "load_server", fail)
    monkeypatch.setattr(sys, "argv", ["run_server.py", "qwen"])

    with pytest.raises(SystemExit) as excinfo:
        run_server.main()

    assert excinfo.value.code == 1
    assert "无法加载服务器" in capsys.readouterr().out


def test_main_starts_registered_server(monkeypatch):
    calls = []
    fake_module = SimpleNamespace(
        PORT=1234,
        mcp=SimpleNamespace(run=lambda **kwargs: calls.append(kwargs)),
    )
    monkeypatch.setitem(run_server.SERVER_MODULES, "fake", "fake.module")
    monkeypatch.setattr(run_server, "load_server", lambda name: fake_module)
    monkeypatch.setattr(sys, "argv", ["run_server.py", "fake"])

    run_server.main()

    assert calls == [
        {"transport": "http", "host": "127.0.0.1", "port": 1234, "path": "/mcp"},
    ]
