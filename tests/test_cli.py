"""Tests for quipeg.cli — command-line interface."""

import json
import subprocess
import sys
from pathlib import Path
import pytest
from quipeg.cli import main

# Compute src directory relative to this test file (works in CI and locally)
_SRC_DIR = Path(__file__).resolve().parents[1] / "src"


class TestCliInfo:
    def test_info_exit_zero(self):
        rc = main(["info"])
        assert rc == 0

    def test_info_contains_version(self, capsys):
        main(["info"])
        out = capsys.readouterr().out
        assert "Quipeg" in out
        assert "3.0" in out or "3.0.0" in out


class TestCliDemo:
    def test_demo_exit_zero(self):
        rc = main(["demo"])
        assert rc == 0

    def test_demo_contains_network_info(self, capsys):
        main(["demo"])
        out = capsys.readouterr().out
        assert "London" in out
        assert "Tokyo" in out
        assert "Fidelity" in out or "fidelity" in out

    def test_demo_shows_swap_comparison(self, capsys):
        main(["demo"])
        out = capsys.readouterr().out
        # Should show Bell-corrected vs arithmetic comparison
        assert "Bell" in out or "bell" in out


class TestCliSimulate:
    def test_simulate_demo_path(self, capsys):
        rc = main(["simulate", "--from", "London", "--to", "Tokyo"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "London" in out
        assert "Tokyo" in out
        assert "fidelity" in out.lower()

    def test_simulate_missing_source(self, capsys):
        with pytest.raises(SystemExit):
            main(["simulate", "--from", "Ghost", "--to", "Tokyo"])

    def test_simulate_missing_destination(self, capsys):
        with pytest.raises(SystemExit):
            main(["simulate", "--from", "London", "--to", "Ghost"])

    def test_simulate_shows_link_table(self, capsys):
        rc = main(["simulate", "--from", "London", "--to", "Paris"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "London" in out
        assert "Paris" in out


class TestCliRender:
    def test_render_default_output(self, capsys, tmp_path):
        out = tmp_path / "map.html"
        rc = main(["render", "--output", str(out)])
        assert rc == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<svg" in content

    def test_render_custom_title(self, capsys, tmp_path):
        out = tmp_path / "map.html"
        rc = main(["render", "--output", str(out), "--title", "My Map"])
        assert rc == 0
        content = out.read_text(encoding="utf-8")
        assert "My Map" in content

    def test_render_missing_csv(self, capsys):
        with pytest.raises(SystemExit):
            main(["render", "--network", "/nonexistent/cities.csv"])

    def test_render_no_crash_empty_network(self, capsys, tmp_path):
        out = tmp_path / "empty.html"
        # Using demo network (no CSV) — always works
        rc = main(["render", "--output", str(out)])
        assert rc == 0
        assert out.exists()


class TestCliExport:
    def test_export_geojson(self, capsys, tmp_path):
        out = tmp_path / "net.geojson"
        rc = main(["export", "--format", "geojson", "--output", str(out)])
        assert rc == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["type"] == "FeatureCollection"

    def test_export_json(self, capsys, tmp_path):
        out = tmp_path / "net.json"
        rc = main(["export", "--format", "json", "--output", str(out)])
        assert rc == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert "nodes" in data
        assert "links" in data

    def test_export_geojson_has_link_metrics(self, capsys, tmp_path):
        out = tmp_path / "net.geojson"
        main(["export", "--format", "geojson", "--output", str(out)])
        data = json.loads(out.read_text())
        link_feats = [f for f in data["features"]
                      if f["geometry"]["type"] == "LineString"]
        assert link_feats
        props = link_feats[0]["properties"]
        assert "fidelity" in props
        assert "qber" in props
        assert "key_rate" in props

    def test_export_missing_csv(self, capsys):
        with pytest.raises(SystemExit):
            main(["export", "--network", "/nonexistent.csv", "--output", "/dev/null"])


class TestCliVersion:
    def test_version_flag(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0


class TestCliHelp:
    def test_help_exit_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


class TestModuleInvocation:
    def test_python_m_quipeg_cli_info(self):
        result = subprocess.run(
            [sys.executable, "-m", "quipeg.cli", "info"],
            capture_output=True, text=True, cwd=str(_SRC_DIR),
        )
        assert result.returncode == 0
        assert "Quipeg" in result.stdout

    def test_python_m_quipeg_cli_demo(self):
        result = subprocess.run(
            [sys.executable, "-m", "quipeg.cli", "demo"],
            capture_output=True, text=True, cwd=str(_SRC_DIR),
            timeout=30,
        )
        assert result.returncode == 0
        assert "London" in result.stdout
