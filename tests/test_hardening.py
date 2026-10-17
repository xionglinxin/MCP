"""Offline tests: no Visio, PowerShell, network listener or real devices."""
import importlib
import inspect
import os
from pathlib import Path
import runpy
import sys
import types
try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib
from unittest.mock import Mock

import pytest
from mcp.server.fastmcp import FastMCP
from setuptools.config.pyprojecttoml import validate

ROOT = Path(os.environ.get("MCP_SOURCE_ROOT", Path(__file__).resolve().parents[1]))


@pytest.fixture
def modules(monkeypatch):
    def load(project, name):
        for key in ("config", "schema", "layout", "session", "drawing", "ensp_driver", "visio_driver", "server"):
            monkeypatch.delitem(sys.modules, key, raising=False)
        monkeypatch.syspath_prepend(str(ROOT / project))
        # Import-only COM doubles. Any accidental COM call fails immediately.
        pythoncom = types.ModuleType("pythoncom")
        win32com = types.ModuleType("win32com")
        client = types.ModuleType("win32com.client")
        win32com.client = client
        monkeypatch.setitem(sys.modules, "pythoncom", pythoncom)
        monkeypatch.setitem(sys.modules, "win32com", win32com)
        monkeypatch.setitem(sys.modules, "win32com.client", client)
        return importlib.import_module(name)
    return load


@pytest.fixture
def drawing(modules, tmp_path, monkeypatch):
    d = modules("visio-draw-mcp", "drawing")
    for key in ("OUTPUT_DIR", "STENCIL_DIR"):
        path = tmp_path / key.lower()
        path.mkdir()
        monkeypatch.setattr(d, key, path)
    return d


def test_stencil_sibling_escape(drawing):
    sibling = drawing.STENCIL_DIR.with_name(drawing.STENCIL_DIR.name + "-outside")
    sibling.mkdir()
    path = sibling / "router.vss"
    path.touch()
    with pytest.raises(ValueError):
        drawing._resolve_stencil_path(str(path))


@pytest.mark.parametrize("suffix", [".vss", ".vssx"])
def test_valid_stencil(drawing, suffix):
    path = drawing.STENCIL_DIR / ("router" + suffix)
    path.touch()
    assert drawing._resolve_stencil_path(path.name) == path


def test_stencil_directory_rejected(drawing):
    (drawing.STENCIL_DIR / "folder.vss").mkdir()
    with pytest.raises(ValueError):
        drawing._resolve_stencil_path("folder.vss")


@pytest.mark.parametrize("operation", ["export", "update", "delete"])
def test_output_sibling_escape(drawing, monkeypatch, operation):
    sibling = drawing.OUTPUT_DIR.with_name(drawing.OUTPUT_DIR.name + "-outside")
    sibling.mkdir()
    path = sibling / "diagram.vsdx"
    path.write_text("untouched")
    invoked = Mock()
    monkeypatch.setattr(drawing, "_with_timeout", invoked)
    if operation == "export":
        result = drawing.export_diagram(str(path))
    elif operation == "update":
        result = drawing.update_diagram({"input_file": str(path)})
    else:
        # No real subprocess even against vulnerable baseline.
        import subprocess
        monkeypatch.setattr(subprocess, "run", Mock(side_effect=OSError("offline")))
        result = drawing.delete_output(str(path))
    assert result["ok"] is False
    assert path.read_text() == "untouched"
    invoked.assert_not_called()


def test_symlink_escape_and_listing(drawing, tmp_path):
    outside = tmp_path / "outside.vsdx"
    outside.write_text("untouched")
    (drawing.OUTPUT_DIR / "escape.vsdx").symlink_to(outside)
    assert drawing.export_diagram(str(drawing.OUTPUT_DIR / "escape.vsdx"))["ok"] is False
    assert drawing.list_outputs()["files"] == []


def test_export_symlink_destination(drawing, tmp_path, monkeypatch):
    source = drawing.OUTPUT_DIR / "diagram.vsdx"
    source.touch()
    outside = tmp_path / "outside.png"
    outside.touch()
    source.with_suffix(".png").symlink_to(outside)
    invoked = Mock()
    monkeypatch.setattr(drawing, "_with_timeout", invoked)
    assert drawing.export_diagram(str(source))["ok"] is False
    invoked.assert_not_called()


def test_valid_export_enters_worker(drawing, monkeypatch):
    path = drawing.OUTPUT_DIR / "diagram.vsdx"
    path.touch()
    invoked = Mock()
    monkeypatch.setattr(drawing, "_with_timeout", invoked)
    assert drawing.export_diagram(str(path))["ok"]
    invoked.assert_called_once()


def test_delete_quote_is_escaped(drawing, monkeypatch):
    import subprocess
    path = drawing.OUTPUT_DIR / "O'Brien.vsdx"
    path.touch()
    calls = []
    def recycle(args, **kwargs):
        calls.append(args)
        path.unlink()
    monkeypatch.setattr(subprocess, "run", recycle)
    assert drawing.delete_output(path.name)["ok"]
    assert "O''Brien.vsdx" in calls[0][-1]


def test_delete_fallback_cannot_escape(drawing, tmp_path, monkeypatch):
    import subprocess
    path = drawing.OUTPUT_DIR / "diagram.vsdx"
    path.touch()
    outside = tmp_path / "trash-outside"
    outside.mkdir()
    (drawing.OUTPUT_DIR / ".trash").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=OSError("offline")))
    assert not drawing.delete_output(path.name)["ok"]
    assert path.exists()
    assert not list(outside.iterdir())


@pytest.mark.parametrize("bad_id", ["rack/router", r"rack\router", "..", "CON", "lpt1", "NUL.txt", "x:y", "a\x00b", "a" * 65])
def test_device_filename_validation(modules, bad_id):
    schema = modules("ensp-mcp", "schema")
    with pytest.raises(ValueError):
        schema.DeviceSpec(id=bad_id, name="router", device_type="AR_Router")


def topology(driver):
    return driver.TopologySpec(title="offline", devices=[driver.DeviceSpec(
        id="R1", name="router", device_type="AR_Router", config_script="display version")])


def test_bundle_generation_unique(modules, monkeypatch, tmp_path):
    d = modules("ensp-mcp", "ensp_driver")
    monkeypatch.setattr(d, "OUTPUT_DIR", tmp_path)
    existing = tmp_path / "previous_bundle"
    existing.mkdir()
    sentinel = existing / "keep.topo"
    sentinel.write_text("existing user artifact")
    # Baseline save_configs defaults to global OUTPUT_DIR, fixed accepts explicit staging dir.
    first = d.generate_topology(topology(d))
    second = d.generate_topology(topology(d))
    assert first["ok"] and second["ok"]
    assert first["topo_file"] != second["topo_file"]
    assert sentinel.read_text() == "existing user artifact"
    for result in (first, second):
        for returned_path in [result["topo_file"], *result["config_files"]]:
            assert Path(returned_path).resolve().is_relative_to(tmp_path.resolve())
        assert Path(result["topo_file"]).is_file()
        assert len(result["config_files"]) == 1
        assert Path(result["config_files"][0]).is_file()
        assert Path(result["config_files"][0]).parent == Path(result["topo_file"]).parent


def test_config_failure_leaves_no_artifacts(modules, monkeypatch, tmp_path):
    d = modules("ensp-mcp", "ensp_driver")
    monkeypatch.setattr(d, "OUTPUT_DIR", tmp_path)
    original = Path.write_text
    def fail_config(self, *args, **kwargs):
        if self.suffix == ".txt":
            raise OSError("synthetic disk failure")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", fail_config)
    assert not d.generate_topology(topology(d))["ok"]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("project", ["ensp-mcp", "visio-draw-mcp"])
def test_real_sdk_http_entrypoint(modules, monkeypatch, project):
    modules(project, "config")
    signature = inspect.signature(FastMCP.run)
    captured = []
    def run(self, *args, **kwargs):
        signature.bind(self, *args, **kwargs)
        captured.append((self.settings.host, self.settings.port, kwargs))
    monkeypatch.setattr(FastMCP, "run", run)
    monkeypatch.setattr(sys, "argv", ["server.py", "--http", "8765"])
    runpy.run_path(str(ROOT / project / "server.py"), run_name="__main__")
    assert captured == [("127.0.0.1", 8765, {"transport": "streamable-http"})]


@pytest.mark.parametrize("project", ["ensp-mcp", "visio-draw-mcp"])
def test_package_metadata(project):
    path = ROOT / project / "pyproject.toml"
    validate(tomllib.loads(path.read_text()), str(path))


@pytest.mark.parametrize("name", ["generate_company_topology", "generate_web_security_topology", "generate_firewall_case_28", "generate_redundant_gateway_topology"])
def test_preset_output_symlink_escape(modules, tmp_path, monkeypatch, name):
    import io
    # Preset scripts reconfigure console encodings at import time.
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    d = modules("visio-draw-mcp", "drawing")
    monkeypatch.delitem(sys.modules, name, raising=False)
    preset = importlib.import_module(name)
    output = tmp_path / "outputs"
    output.mkdir()
    monkeypatch.setattr(preset, "OUTPUT_DIR", output)
    if hasattr(preset, "ensure_stencil"):
        monkeypatch.setattr(preset, "ensure_stencil", lambda: None)
    outside = tmp_path / "outside.vsdx"
    outside.write_text("untouched")
    (output / f"{preset.OUTPUT_STEM}.vsdx").symlink_to(outside)
    with pytest.raises(ValueError):
        preset.generate()
    assert outside.read_text() == "untouched"


def test_output_resource_hides_staging(modules, monkeypatch, tmp_path):
    server = modules("ensp-mcp", "server")
    monkeypatch.setattr(server, "OUTPUT_DIR", tmp_path)
    stage = tmp_path / ".staging-incomplete"
    stage.mkdir()
    (stage / "hidden.topo").touch()
    bundle = tmp_path / "complete"
    bundle.mkdir()
    (bundle / "diagram.topo").touch()
    (tmp_path / "legacy.topo").touch()
    assert server.output_list_resource().splitlines() == [str(Path("complete") / "diagram.topo"), "legacy.topo"]
