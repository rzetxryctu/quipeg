"""Tests for quipeg.render — HTML topology visualizer."""

import os
import tempfile
import pytest
from quipeg.network import QuantumNetwork, NodeRole
from quipeg.render import to_html, save_html


@pytest.fixture
def sample_network():
    """A small demo network for rendering tests."""
    net = QuantumNetwork(name="Test Network")
    for name, lat, lon, role in [
        ("London", 51.5, -0.1, "backbone"),
        ("Paris", 48.9, 2.4, "repeater"),
        ("Frankfurt", 50.1, 8.7, "endpoint"),
    ]:
        net.add_node(name, lat, lon, role=role)
    net.add_link("London", "Paris", fidelity=0.95)
    net.add_link("Paris", "Frankfurt", fidelity=0.88)
    return net


class TestToHtml:
    def test_returns_string(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0)
        net.add_node("B", 1, 1)
        net.add_link("A", "B")
        html = to_html(net)
        assert isinstance(html, str)

    def test_contains_svg_tag(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0)
        net.add_node("B", 1, 1)
        net.add_link("A", "B")
        html = to_html(net)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_title(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0)
        html = to_html(net, title="My Custom Title")
        assert "My Custom Title" in html

    def test_contains_node_names(self, sample_network):
        html = to_html(sample_network)
        for name in ["London", "Paris", "Frankfurt"]:
            assert name in html

    def test_contains_fidelity_in_tooltip(self, sample_network):
        html = to_html(sample_network)
        assert "F=" in html
        assert "QBER=" in html

    def test_no_external_dependencies(self, sample_network):
        html = to_html(sample_network)
        # No CDN links, no http://, no https://, no external fonts
        for prefix in ["http://", "https://", "cdn.", "fonts.googleapis"]:
            # Allow standard SVG namespace attribute
            normalized = html.lower().replace("http://www.w3.org/2000/svg", "")
            assert prefix.lower() not in normalized

    def test_empty_network_renders(self):
        net = QuantumNetwork()
        html = to_html(net)
        assert "<svg" in html

    def test_custom_dimensions(self, sample_network):
        html = to_html(sample_network, width=1200, height=600)
        assert 'width="1200"' in html
        assert 'height="600"' in html

    def test_contains_legend(self, sample_network):
        html = to_html(sample_network)
        assert "Endpoint" in html or "endpoint" in html.lower()

    def test_includes_javascript_interaction(self, sample_network):
        html = to_html(sample_network)
        assert "<script" in html or "mouseenter" in html

    def test_link_lines_present(self, sample_network):
        html = to_html(sample_network)
        assert "<line" in html

    def test_node_circles_present(self, sample_network):
        html = to_html(sample_network)
        assert "<circle" in html

    def test_inactive_link_distinguished(self, sample_network):
        link = sample_network.get_link("London", "Paris")
        link.active = False
        html = to_html(sample_network)
        assert "opacity" in html.lower() or "stroke-opacity" in html.lower()


class TestSaveHtml:
    def test_saves_file(self, sample_network, tmp_path):
        out = tmp_path / "map.html"
        save_html(sample_network, str(out))
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<svg" in content

    def test_overwrites_existing(self, sample_network, tmp_path):
        out = tmp_path / "map.html"
        save_html(sample_network, str(out))
        save_html(sample_network, str(out))  # should not raise
        assert out.exists()

    def test_roundtrip_content(self, sample_network, tmp_path):
        out = tmp_path / "map.html"
        save_html(sample_network, str(out))
        content = out.read_text(encoding="utf-8")
        # Should contain all node names
        for name in ["London", "Paris", "Frankfurt"]:
            assert name in content


class TestSvgProjection:
    """Test the equirectangular projection helper."""

    def test_single_node_centered(self):
        net = QuantumNetwork()
        net.add_node("Solo", 0.0, 0.0)
        html = to_html(net)
        assert "Solo" in html
        assert "<svg" in html

    def test_multiple_nodes_same_coords(self):
        # Two nodes at the same spot — should not crash
        net = QuantumNetwork()
        net.add_node("A", 0.0, 0.0)
        net.add_node("B", 0.0, 0.0)
        net.add_link("A", "B")
        html = to_html(net)
        assert "<svg" in html

    def test_extreme_coordinates(self):
        net = QuantumNetwork()
        net.add_node("North", 90.0, 0.0)
        net.add_node("South", -90.0, 0.0)
        net.add_node("East", 0.0, 180.0)
        net.add_node("West", 0.0, -180.0)
        net.add_link("North", "South")
        net.add_link("East", "West")
        html = to_html(net)
        assert "<svg" in html
