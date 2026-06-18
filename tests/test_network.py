"""Tests for quipeg.network — QuantumNetwork, QuantumNode, QuantumLink."""

import math
import json
import pytest
from quipeg.network import (
    QuantumNetwork,
    QuantumNode,
    QuantumLink,
    NodeRole,
    load_csv,
)
from quipeg.physics import swap_fidelity_bell


# ---------------------------------------------------------------------------
# QuantumNode
# ---------------------------------------------------------------------------

class TestQuantumNode:
    def test_basic_creation(self):
        n = QuantumNode("Test", 0.0, 0.0)
        assert n.name == "Test"
        assert n.lat == 0.0
        assert n.lon == 0.0
        assert n.role == NodeRole.ENDPOINT
        assert n.fidelity == 1.0

    def test_is_repeater_endpoint(self):
        n = QuantumNode("A", 0, 0, role=NodeRole.ENDPOINT)
        assert not n.is_repeater

    def test_is_repeater_true(self):
        n = QuantumNode("A", 0, 0, role=NodeRole.REPEATER)
        assert n.is_repeater

    def test_is_repeater_backbone(self):
        n = QuantumNode("A", 0, 0, role=NodeRole.BACKBONE)
        assert n.is_repeater


# ---------------------------------------------------------------------------
# QuantumLink
# ---------------------------------------------------------------------------

class TestQuantumLink:
    def test_basic_creation(self):
        link = QuantumLink("A", "B", distance_km=100.0, fidelity=0.95)
        assert link.a == "A"
        assert link.b == "B"
        assert link.distance_km == 100.0
        assert link.fidelity == 0.95
        assert link.active

    def test_transmittance_property(self):
        link = QuantumLink("A", "B", distance_km=50.0)
        assert 0.0 < link.transmittance < 1.0

    def test_qber_property(self):
        link = QuantumLink("A", "B", distance_km=10.0, fidelity=0.90)
        assert 0.0 <= link.qber <= 0.375

    def test_key_rate_property(self):
        link = QuantumLink("A", "B", distance_km=10.0, fidelity=0.97)
        assert link.key_rate >= 0.0

    def test_to_dict_from_dict_roundtrip(self):
        original = QuantumLink("X", "Y", distance_km=55.5, fidelity=0.88,
                               age_seconds=1.5, active=False)
        d = original.to_dict()
        restored = QuantumLink.from_dict(d)
        assert restored.a == original.a
        assert restored.b == original.b
        assert math.isclose(restored.distance_km, original.distance_km)
        assert math.isclose(restored.fidelity, original.fidelity)
        assert math.isclose(restored.age_seconds, original.age_seconds)
        assert restored.active == original.active


# ---------------------------------------------------------------------------
# QuantumNetwork — basic
# ---------------------------------------------------------------------------

class TestQuantumNetworkBasic:
    def test_empty_network(self):
        net = QuantumNetwork()
        assert net.name == "World"
        assert net.node_count() == 0
        assert net.link_count() == 0

    def test_custom_name(self):
        net = QuantumNetwork(name="TestNet")
        assert net.name == "TestNet"

    def test_add_node(self):
        net = QuantumNetwork()
        node = net.add_node("London", 51.5, -0.1)
        assert node.name == "London"
        assert net.node_count() == 1
        assert "London" in net.node_names()

    def test_add_node_duplicate_raises(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0)
        with pytest.raises(ValueError):
            net.add_node("A", 1, 1)

    def test_add_node_with_role_string(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0, role="repeater")
        assert net.get_node("A").role == NodeRole.REPEATER

    def test_add_node_with_role_enum(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0, role=NodeRole.BACKBONE)
        assert net.get_node("A").role == NodeRole.BACKBONE

    def test_get_node(self):
        net = QuantumNetwork()
        net.add_node("X", 10.0, 20.0)
        node = net.get_node("X")
        assert node.lat == 10.0
        assert node.lon == 20.0

    def test_get_node_missing_raises(self):
        net = QuantumNetwork()
        with pytest.raises(KeyError):
            net.get_node("Ghost")

    def test_nodes_returns_in_order(self):
        net = QuantumNetwork()
        net.add_node("C", 0, 0)
        net.add_node("A", 0, 0)
        net.add_node("B", 0, 0)
        assert [n.name for n in net.nodes()] == ["C", "A", "B"]


# ---------------------------------------------------------------------------
# QuantumNetwork — links
# ---------------------------------------------------------------------------

class TestQuantumNetworkLinks:
    def setup_method(self):
        self.net = QuantumNetwork()
        self.net.add_node("A", 0.0, 0.0)
        self.net.add_node("B", 1.0, 1.0)
        self.net.add_node("C", 2.0, 2.0)

    def test_add_link(self):
        link = self.net.add_link("A", "B")
        assert link.distance_km > 0
        assert self.net.link_count() == 1

    def test_add_link_auto_distance(self):
        link = self.net.add_link("A", "B")
        # Haversine of (0,0) to (1,1) ≈ 157 km
        assert 100 < link.distance_km < 200

    def test_add_link_missing_node_raises(self):
        with pytest.raises(KeyError):
            self.net.add_link("A", "Ghost")

    def test_add_link_duplicate_raises(self):
        self.net.add_link("A", "B")
        with pytest.raises(ValueError):
            self.net.add_link("A", "B")
        with pytest.raises(ValueError):
            self.net.add_link("B", "A")  # undirected

    def test_has_link(self):
        self.net.add_link("A", "B")
        assert self.net.has_link("A", "B")
        assert self.net.has_link("B", "A")
        assert not self.net.has_link("A", "C")

    def test_get_link(self):
        self.net.add_link("A", "B")
        link = self.net.get_link("A", "B")
        assert link.a == "A" and link.b == "B"

    def test_neighbors(self):
        self.net.add_link("A", "B")
        self.net.add_link("A", "C")
        assert set(self.net.neighbors("A")) == {"B", "C"}

    def test_links_returns_in_order(self):
        self.net.add_link("A", "B")
        self.net.add_link("B", "C")
        assert [l.a for l in self.net.links()] == ["A", "B"]


# ---------------------------------------------------------------------------
# QuantumNetwork — Dijkstra shortest path
# ---------------------------------------------------------------------------

class TestShortestPath:
    def setup_method(self):
        self.net = QuantumNetwork()
        for name, lat, lon in [
            ("S", 0, 0), ("A", 1, 0), ("B", 2, 0),
            ("C", 0, 1), ("D", 1, 1), ("E", 2, 1), ("T", 3, 1),
        ]:
            self.net.add_node(name, lat, lon)
        # Linear: S-A-B-T
        self.net.add_link("S", "A")
        self.net.add_link("A", "B")
        self.net.add_link("B", "T")
        # Alternative detour: S-C-D-E-T (longer)
        self.net.add_link("S", "C")
        self.net.add_link("C", "D")
        self.net.add_link("D", "E")
        self.net.add_link("E", "T")

    def test_direct_path(self):
        path = self.net.shortest_path("S", "T")
        # Should prefer the shorter 3-hop path over the 5-hop one
        assert path[0] == "S"
        assert path[-1] == "T"
        assert len(path) == 4

    def test_same_node(self):
        assert self.net.shortest_path("A", "A") == ["A"]

    def test_missing_node_raises(self):
        with pytest.raises(KeyError):
            self.net.shortest_path("A", "Ghost")

    def test_no_path(self):
        net = QuantumNetwork()
        net.add_node("X", 0, 0)
        net.add_node("Y", 10, 10)
        assert net.shortest_path("X", "Y") == []


# ---------------------------------------------------------------------------
# QuantumNetwork — end-to-end fidelity
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def setup_method(self):
        self.net = QuantumNetwork()
        for name, lat, lon, role in [
            ("A", 0, 0, "endpoint"), ("B", 1, 0, "repeater"),
            ("C", 2, 0, "repeater"), ("D", 3, 0, "endpoint"),
        ]:
            self.net.add_node(name, lat, lon, role=role)
        self.net.add_link("A", "B", fidelity=0.95)
        self.net.add_link("B", "C", fidelity=0.95)
        self.net.add_link("C", "D", fidelity=0.95)

    def test_end_to_end_returns_fidelity(self):
        f, skr, diag = self.net.end_to_end("A", "D")
        assert 0.25 < f < 0.95
        assert skr >= 0
        assert "path" in diag
        assert "hop_count" in diag

    def test_end_to_end_diagnostics_contain_link_details(self):
        _, _, diag = self.net.end_to_end("A", "D")
        assert len(diag["link_details"]) == 3
        for detail in diag["link_details"]:
            assert "fidelity" in detail
            assert "distance_km" in detail
            assert "qber" in detail

    def test_end_to_end_no_path_raises(self):
        net = QuantumNetwork()
        net.add_node("X", 0, 0)
        net.add_node("Y", 10, 10)
        with pytest.raises(ValueError):
            net.end_to_end("X", "Y")

    def test_end_to_end_missing_node_raises(self):
        with pytest.raises(KeyError):
            self.net.end_to_end("A", "Ghost")

    def test_end_to_end_single_link(self):
        self.net.add_node("E", 0.5, 0)
        self.net.add_link("A", "E", fidelity=0.99)
        f, _, _ = self.net.end_to_end("A", "E")
        assert 0.25 < f <= 1.0

    def test_bell_corrected_vs_arithmetic(self):
        # With imperfect fidelity, Bell-corrected should give
        # lower fidelity than arithmetic mean
        net = QuantumNetwork()
        for name, lat, lon in [("A", 0, 0), ("B", 1, 0), ("C", 2, 0)]:
            net.add_node(name, lat, lon)
        net.add_link("A", "B", fidelity=0.80)
        net.add_link("B", "C", fidelity=0.80)

        f_bell, _, _ = net.end_to_end("A", "C", use_bell_corrected=True)

        net2 = QuantumNetwork()
        for name, lat, lon in [("A", 0, 0), ("B", 1, 0), ("C", 2, 0)]:
            net2.add_node(name, lat, lon)
        net2.add_link("A", "B", fidelity=0.80)
        net2.add_link("B", "C", fidelity=0.80)
        f_avg, _, _ = net2.end_to_end("A", "C", use_bell_corrected=False)

        # Bell-corrected should be lower than or equal to avg
        assert f_bell <= f_avg + 1e-9


# ---------------------------------------------------------------------------
# QuantumNetwork — fidelity_path
# ---------------------------------------------------------------------------

class TestFidelityPath:
    def setup_method(self):
        self.net = QuantumNetwork()
        for name, lat, lon in [("A", 0, 0), ("B", 1, 0), ("C", 2, 0)]:
            self.net.add_node(name, lat, lon)
        self.net.add_link("A", "B", fidelity=0.95)
        self.net.add_link("B", "C", fidelity=0.95)

    def test_fidelity_path_returns_path(self):
        path, f, diag = self.net.fidelity_path("A", "C")
        assert path[0] == "A"
        assert path[-1] == "C"
        assert 0.25 < f <= 1.0
        assert "hop_count" in diag

    def test_fidelity_path_same_node(self):
        path, f, diag = self.net.fidelity_path("A", "A")
        assert path == ["A"]
        assert f == 1.0
        assert diag["hop_count"] == 0


# ---------------------------------------------------------------------------
# MST backbone
# ---------------------------------------------------------------------------

class TestBackbone:
    def test_backbone_empty(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0, population=100)
        assert net.build_backbone().node_count() == 1

    def test_backbone_mst_connects_all(self):
        net = QuantumNetwork()
        for name, lat, lon, pop in [
            ("A", 0, 0, 1_000_000), ("B", 1, 0, 2_000_000),
            ("C", 2, 0, 3_000_000),
        ]:
            net.add_node(name, lat, lon, population=pop)
        backbone = net.build_backbone(min_population=0)
        assert backbone.node_count() == 3
        # MST with 3 nodes has exactly 2 edges
        assert backbone.link_count() == 2

    def test_backbone_respects_population_threshold(self):
        net = QuantumNetwork()
        for name, lat, lon, pop in [
            ("Big", 0, 0, 5_000_000), ("Small", 1, 1, 100),
        ]:
            net.add_node(name, lat, lon, population=pop)
        backbone = net.build_backbone(min_population=1_000_000)
        assert backbone.node_count() == 1
        assert backbone.link_count() == 0


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestSerialization:
    def setup_method(self):
        self.net = QuantumNetwork(name="TestNet")
        self.net.add_node("X", 10.0, 20.0, population=1_000_000, role=NodeRole.REPEATER)
        self.net.add_node("Y", 11.0, 21.0, population=2_000_000)
        self.net.add_link("X", "Y", fidelity=0.95)
        self.net._current_time_seconds = 5.0

    def test_to_json_string(self):
        s = self.net.to_json()
        d = json.loads(s)
        assert d["name"] == "TestNet"
        assert d["version"] == "3.0.0"
        assert len(d["nodes"]) == 2
        assert len(d["links"]) == 1

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "net.json"
        self.net.save(str(path))
        loaded = QuantumNetwork.load(str(path))
        assert loaded.name == self.net.name
        assert loaded.node_count() == self.net.node_count()
        assert loaded.link_count() == self.net.link_count()
        assert loaded._current_time_seconds == self.net._current_time_seconds
        # Check fidelity preserved
        loaded_link = loaded.get_link("X", "Y")
        orig_link = self.net.get_link("X", "Y")
        assert math.isclose(loaded_link.fidelity, orig_link.fidelity)

    def test_from_dict(self):
        d = {
            "name": "FromDict",
            "nodes": [
                {"name": "P", "lat": 0.0, "lon": 0.0, "population": 100, "role": "endpoint", "fidelity": 1.0},
                {"name": "Q", "lat": 1.0, "lon": 1.0, "population": 200, "role": "repeater", "fidelity": 0.9},
            ],
            "links": [],
            "current_time_seconds": 0.0,
        }
        net = QuantumNetwork.from_dict(d)
        assert net.node_count() == 2
        assert net.get_node("Q").role == NodeRole.REPEATER


# ---------------------------------------------------------------------------
# GeoJSON export
# ---------------------------------------------------------------------------

class TestGeoJSON:
    def setup_method(self):
        self.net = QuantumNetwork()
        self.net.add_node("A", 0, 0, role=NodeRole.ENDPOINT)
        self.net.add_node("B", 1, 1, role=NodeRole.REPEATER)
        self.net.add_link("A", "B")

    def test_geojson_structure(self):
        gj = self.net.to_geojson()
        assert gj["type"] == "FeatureCollection"
        assert "features" in gj

    def test_geojson_node_features(self):
        gj = self.net.to_geojson()
        node_feats = [f for f in gj["features"] if f["geometry"]["type"] == "Point"]
        assert len(node_feats) == 2

    def test_geojson_link_features(self):
        gj = self.net.to_geojson()
        link_feats = [f for f in gj["features"] if f["geometry"]["type"] == "LineString"]
        assert len(link_feats) == 1

    def test_geojson_link_has_metrics(self):
        gj = self.net.to_geojson()
        link_feats = [f for f in gj["features"] if f["geometry"]["type"] == "LineString"]
        props = link_feats[0]["properties"]
        assert "fidelity" in props
        assert "qber" in props
        assert "key_rate" in props
        assert "distance_km" in props


# ---------------------------------------------------------------------------
# Time evolution
# ---------------------------------------------------------------------------

class TestTimeEvolution:
    def setup_method(self):
        self.net = QuantumNetwork()
        self.net.add_node("A", 0, 0)
        self.net.add_node("B", 1, 1)
        self.net.add_link("A", "B", fidelity=0.95)

    def test_advance_time_updates_clock(self):
        self.net.advance_time(1.0)
        assert self.net._current_time_seconds == 1.0

    def test_advance_time_decays_fidelity(self):
        original_f = self.net.get_link("A", "B").fidelity
        self.net.advance_time(1.0, use_t1_t2=False)
        assert self.net.get_link("A", "B").fidelity < original_f

    def test_advance_time_t1_t2(self):
        original_f = self.net.get_link("A", "B").fidelity
        self.net.advance_time(0.5, use_t1_t2=True)
        assert self.net.get_link("A", "B").fidelity < original_f

    def test_negative_dt_ignored(self):
        self.net.advance_time(-10.0)
        assert self.net._current_time_seconds == 0.0


# ---------------------------------------------------------------------------
# Summary / repr
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_string(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0)
        net.add_node("B", 1, 1)
        net.add_link("A", "B")
        s = net.summary()
        assert "QuantumNetwork" in s
        assert "2 nodes" in s
        assert "1 links" in s

    def test_repr(self):
        net = QuantumNetwork(name="X")
        assert repr(net) == net.summary()

    def test_len(self):
        net = QuantumNetwork()
        net.add_node("A", 0, 0)
        net.add_node("B", 1, 1)
        assert len(net) == 2
