"""
QuantumNetwork — the core simulator class.

Represents a QKD network as a weighted graph where vertices are relay
nodes (cities / data centres) and edges are optical-fibre links.
Each link carries a physical model (distance, transmittance, fidelity).
"""

from __future__ import annotations

import csv
import heapq
import json
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set

from quipeg.physics import (
    haversine,
    transmittance,
    decohere,
    decohere_t1_t2,
    swap_fidelity,
    swap_fidelity_bell,
    secret_key_rate,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class NodeRole(Enum):
    """Role of a quantum network node."""
    ENDPOINT = "endpoint"
    REPEATER = "repeater"
    BACKBONE = "backbone"


@dataclass
class QuantumNode:
    """
    Quantum network node / relay point.

    Attributes
    ----------
    name : str
        Human-readable identifier (city name or node ID).
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.
    population : int
        City / metro-area population (for backbone selection).
    role : NodeRole
        Whether this node is an endpoint, repeater, or backbone hub.
    fidelity : float
        Average Bell-state fidelity of entanglement generated at this node.
    """
    name: str
    lat: float
    lon: float
    population: int = 0
    role: NodeRole = NodeRole.ENDPOINT
    fidelity: float = 1.0

    @property
    def is_repeater(self) -> bool:
        """True if this node is a quantum repeater."""
        return self.role in (NodeRole.REPEATER, NodeRole.BACKBONE)


@dataclass
class QuantumLink:
    """
    Bidirectional optical-fibre link between two nodes.

    Attributes
    ----------
    a : str
        First node name.
    b : str
        Second node name.
    distance_km : float
        Great-circle distance in km (approximated as fibre distance).
    fidelity : float
        Current Bell-state fidelity of entanglement distributed on this link.
    age_seconds : float
        Elapsed time since last entanglement generation (s).
    active : bool
        Whether the link currently carries usable entanglement.
    """
    a: str
    b: str
    distance_km: float
    fidelity: float = 1.0
    age_seconds: float = 0.0
    active: bool = True

    @property
    def transmittance(self) -> float:
        """Photon transmittance of this link."""
        return transmittance(self.distance_km)

    @property
    def qber(self) -> float:
        """Estimated quantum bit error rate."""
        return max(0.0, (1.0 - self.fidelity) / 2.0)

    @property
    def key_rate(self) -> float:
        """Estimated secret key rate (bits/s) for this link."""
        skr, _ = secret_key_rate(self.fidelity, self.distance_km)
        return skr

    def to_dict(self) -> dict:
        """Serialise link to a plain dict."""
        return {
            "a": self.a,
            "b": self.b,
            "distance_km": round(self.distance_km, 6),
            "fidelity": round(self.fidelity, 6),
            "age_seconds": round(self.age_seconds, 6),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuantumLink":
        """Reconstruct a link from a plain dict."""
        return cls(
            a=d["a"],
            b=d["b"],
            distance_km=d["distance_km"],
            fidelity=d.get("fidelity", 1.0),
            age_seconds=d.get("age_seconds", 0.0),
            active=d.get("active", True),
        )


# ---------------------------------------------------------------------------
# CSV utility
# ---------------------------------------------------------------------------

def load_csv(
    path: str,
    city_col: str = "city",
    lat_col: str = "lat",
    lon_col: str = "lon",
    pop_col: str = "population",
) -> List[QuantumNode]:
    """
    Load network nodes from a CSV file.

    Parameters
    ----------
    path : str
        Path to the CSV file.
    city_col, lat_col, lon_col, pop_col : str
        Expected header names (case-insensitive matching).

    Returns
    -------
    List[QuantumNode]

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If required columns are missing.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        headers = {h.lower().strip(): h for h in reader.fieldnames or []}

        def find(*names: str) -> str:
            for n in names:
                key = n.lower().strip()
                if key in headers:
                    return headers[key]
            raise ValueError(f"CSV missing one of: {names}")

        c_col = find(city_col, "city", "name")
        la_col = find(lat_col, "lat", "latitude", "y")
        lo_col = find(lon_col, "lon", "lng", "longitude", "x")
        try:
            po_col = find(pop_col, "population", "pop", "pop_total")
        except ValueError:
            po_col = None

        nodes: List[QuantumNode] = []
        for row in reader:
            city = row[c_col].strip()
            try:
                lat = float(row[la_col])
                lon = float(row[lo_col])
            except ValueError:
                continue
            try:
                pop = int(row[po_col]) if po_col and row.get(po_col, "").strip() else 0
            except ValueError:
                pop = 0
            nodes.append(QuantumNode(name=city, lat=lat, lon=lon, population=pop))

        return nodes


# ---------------------------------------------------------------------------
# QuantumNetwork
# ---------------------------------------------------------------------------

class QuantumNetwork:
    """
    Top-level simulator for a planetary quantum communication backbone.

    Parameters
    ----------
    name : str, optional
        Human-readable name for this network instance (default "World").

    Examples
    --------
    >>> net = QuantumNetwork()
    >>> net.add_node("London", 51.5, -0.1, population=9_000_000, role=NodeRole.REPEATER)
    >>> net.add_node("Paris", 48.9, 2.4, population=2_100_000, role=NodeRole.REPEATER)
    >>> net.add_link("London", "Paris")
    >>> net.shortest_path("London", "Paris")
    ['London', 'Paris']
    >>> print(net.summary())
    """

    def __init__(self, name: str = "World"):
        self.name = name
        self._nodes: Dict[str, QuantumNode] = {}
        self._links: Dict[Tuple[str, str], QuantumLink] = {}
        self._current_time_seconds: float = 0.0

    # ------------------------------------------------------------------
    # Node API
    # ------------------------------------------------------------------

    def add_node(
        self,
        name: str,
        lat: float,
        lon: float,
        population: int = 0,
        role: NodeRole | str = NodeRole.ENDPOINT,
    ) -> QuantumNode:
        """
        Register a network node (city / relay station).

        Parameters
        ----------
        name : str
            Node identifier.
        lat, lon : float
            Geographic coordinates in decimal degrees.
        population : int, optional
            Metropolitan population.
        role : NodeRole or str, optional
            Node role (default ENDPOINT). Accepts a NodeRole enum or a
            string: "endpoint", "repeater", "backbone".

        Returns
        -------
        QuantumNode

        Raises
        ------
        ValueError
            If a node with the same name already exists.
        """
        if name in self._nodes:
            raise ValueError(f"Node {name!r} already exists")
        if isinstance(role, str):
            role_map = {
                "endpoint": NodeRole.ENDPOINT,
                "repeater": NodeRole.REPEATER,
                "backbone": NodeRole.BACKBONE,
            }
            role = role_map.get(role.lower(), NodeRole.ENDPOINT)
        node = QuantumNode(
            name=name, lat=lat, lon=lon,
            population=population, role=role,
        )
        self._nodes[name] = node
        return node

    def get_node(self, name: str) -> QuantumNode:
        """Return the QuantumNode object for ``name``."""
        return self._nodes[name]

    def node_count(self) -> int:
        """Number of registered nodes."""
        return len(self._nodes)

    def nodes(self) -> List[QuantumNode]:
        """All registered nodes, in insertion order."""
        return list(self._nodes.values())

    def node_names(self) -> List[str]:
        """All registered node names."""
        return list(self._nodes.keys())

    # ------------------------------------------------------------------
    # Link API
    # ------------------------------------------------------------------

    def add_link(
        self,
        a: str,
        b: str,
        fidelity: float = 1.0,
    ) -> QuantumLink:
        """
        Add a bidirectional optical-fibre link between two nodes.

        Distance is auto-computed via Haversine from node coordinates.

        Parameters
        ----------
        a, b : str
            Names of the two endpoint nodes.
        fidelity : float, optional
            Initial Bell-state fidelity (default 1.0).

        Returns
        -------
        QuantumLink

        Raises
        ------
        KeyError
            If either endpoint is not registered.
        ValueError
            If a link between a and b already exists.
        """
        if a not in self._nodes or b not in self._nodes:
            raise KeyError("Both endpoints must be registered nodes")
        key = tuple(sorted((a, b)))
        if key in self._links:
            raise ValueError(f"Link {a!r}–{b!r} already exists")
        dist = haversine(
            self._nodes[a].lat, self._nodes[a].lon,
            self._nodes[b].lat, self._nodes[b].lon,
        )
        link = QuantumLink(a=a, b=b, distance_km=dist, fidelity=fidelity)
        self._links[key] = link
        return link

    def has_link(self, a: str, b: str) -> bool:
        """True iff a link between a and b exists (undirected)."""
        key = tuple(sorted((a, b)))
        return key in self._links

    def get_link(self, a: str, b: str) -> QuantumLink:
        """Return the QuantumLink between a and b."""
        key = tuple(sorted((a, b)))
        return self._links[key]

    def link_count(self) -> int:
        """Number of links."""
        return len(self._links)

    def links(self) -> List[QuantumLink]:
        """All links, in insertion order."""
        return list(self._links.values())

    def neighbors(self, name: str) -> List[str]:
        """Names of all nodes directly connected to ``name``."""
        result: List[str] = []
        for link in self._links.values():
            if link.a == name:
                result.append(link.b)
            elif link.b == name:
                result.append(link.a)
        return result

    # ------------------------------------------------------------------
    # Adjacency helper
    # ------------------------------------------------------------------

    def _adjacency(self) -> Dict[str, List[Tuple[str, float]]]:
        """Dijkstra-friendly adjacency list: node → [(neighbor, dist_km)]."""
        adj: Dict[str, List[Tuple[str, float]]] = {n: [] for n in self._nodes}
        for link in self._links.values():
            adj[link.a].append((link.b, link.distance_km))
            adj[link.b].append((link.a, link.distance_km))
        return adj

    # ------------------------------------------------------------------
    # Routing — Dijkstra shortest path (physical distance)
    # ------------------------------------------------------------------

    def shortest_path(self, a: str, b: str) -> List[str]:
        """
        Shortest path (fewest km) between two nodes via Dijkstra's algorithm.

        Parameters
        ----------
        a, b : str
            Source and destination node names.

        Returns
        -------
        List[str]
            Ordered list of node names, or empty list if unreachable.

        Examples
        --------
        >>> net = QuantumNetwork()
        >>> net.add_node("A", 0, 0); net.add_node("B", 1, 1); net.add_link("A", "B")
        >>> net.shortest_path("A", "B")
        ['A', 'B']
        """
        if a not in self._nodes or b not in self._nodes:
            raise KeyError("Source and target must be registered nodes")
        if a == b:
            return [a]

        graph = self._adjacency()
        dist: Dict[str, float] = {n: float("inf") for n in self._nodes}
        prev: Dict[str, Optional[str]] = {n: None for n in self._nodes}
        dist[a] = 0.0
        heap: List[Tuple[float, str]] = [(0.0, a)]
        visited: Set[str] = set()

        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            if u == b:
                break
            for v, w in graph.get(u, []):
                if v in visited:
                    continue
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))

        if prev[b] is None:
            return []

        # reconstruct path
        path: List[str] = []
        cur: Optional[str] = b
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    # ------------------------------------------------------------------
    # End-to-end fidelity via Bell-corrected entanglement swapping
    # ------------------------------------------------------------------

    def end_to_end(
        self,
        a: str,
        b: str,
        use_bell_corrected: bool = True,
    ) -> Tuple[float, float, dict]:
        """
        Compute end-to-end fidelity and SKR estimate along the shortest path.

        Fidelity is accumulated by performing entanglement swapping
        (Bell-corrected product model in v3.0) at each intermediate node.
        SKR is estimated for the full path using the BB84 model at each link.

        Parameters
        ----------
        a, b : str
            Source and destination node names.
        use_bell_corrected : bool, optional
            Use Bell-corrected product model (default True). Set False
            to use the v2.0 arithmetic-mean model for comparison.

        Returns
        -------
        Tuple[float, float, dict]
            (end_to_end_fidelity, estimated_SKR_bits_per_s, diagnostics_dict).

        Raises
        ------
        KeyError
            If a or b are not registered nodes.
        ValueError
            If no path exists between a and b.

        Examples
        --------
        >>> net = QuantumNetwork()
        >>> net.add_node("A", 0, 0, role=NodeRole.REPEATER)
        >>> net.add_node("B", 1, 0, role=NodeRole.REPEATER)
        >>> net.add_node("C", 2, 0, role=NodeRole.REPEATER)
        >>> net.add_link("A", "B", fidelity=0.95)
        >>> net.add_link("B", "C", fidelity=0.95)
        >>> f, skr, diag = net.end_to_end("A", "C")
        >>> 0.25 < f < 0.95
        True
        """
        if a not in self._nodes or b not in self._nodes:
            raise KeyError("Source and target must be registered nodes")
        path = self.shortest_path(a, b)
        if not path:
            raise ValueError(f"No path exists between {a!r} and {b!r}")

        swap_fn = swap_fidelity_bell if use_bell_corrected else swap_fidelity

        # Accumulate fidelity along path via swaps
        f_e2e = 1.0
        for i in range(len(path) - 1):
            link = self.get_link(path[i], path[i + 1])
            f_e2e = swap_fn(f_e2e, link.fidelity)

        # Path SKR estimate: minimum link SKR (bottleneck)
        min_skr = float("inf")
        total_dist = 0.0
        link_details: List[dict] = []
        for i in range(len(path) - 1):
            link = self.get_link(path[i], path[i + 1])
            skr, info = secret_key_rate(link.fidelity, link.distance_km)
            total_dist += link.distance_km
            link_details.append({
                "link": f"{link.a}–{link.b}",
                "distance_km": round(link.distance_km, 3),
                "fidelity": round(link.fidelity, 6),
                "qber": round(link.qber, 6),
                "skr": round(skr, 2),
            })
            if skr < min_skr:
                min_skr = skr

        skr_estimate = min_skr if min_skr != float("inf") else 0.0

        diagnostics = {
            "path": path,
            "hop_count": len(path) - 1,
            "total_distance_km": round(total_dist, 3),
            "link_details": link_details,
            "use_bell_corrected": use_bell_corrected,
        }

        return f_e2e, skr_estimate, diagnostics

    # ------------------------------------------------------------------
    # Fidelity-aware path (maximise fidelity, account for loss)
    # ------------------------------------------------------------------

    def fidelity_path(self, a: str, b: str) -> Tuple[List[str], Optional[float], Optional[dict]]:
        """
        Find the path between source and target that maximises end-to-end
        Bell-state fidelity, accounting for fibre transmittance and Bell-corrected
        entanglement swapping.

        Uses a modified Dijkstra where the weight is negative log-survival,
        and fidelity is accumulated via the Bell-corrected product formula.

        Parameters
        ----------
        a, b : str
            Source and destination node names.

        Returns
        -------
        Tuple[List[str], float or None, dict or None]
            (best_path, end_to_end_fidelity, diagnostics).

        Raises
        ------
        KeyError
            If a or b are not registered nodes.

        Examples
        --------
        >>> net = QuantumNetwork()
        >>> net.add_node("A", 0, 0, role=NodeRole.REPEATER)
        >>> net.add_node("B", 1, 0, role=NodeRole.REPEATER)
        >>> net.add_node("C", 2, 0, role=NodeRole.REPEATER)
        >>> net.add_link("A", "B", fidelity=0.95)
        >>> net.add_link("B", "C", fidelity=0.95)
        >>> path, f, diag = net.fidelity_path("A", "C")
        >>> path[0], path[-1]
        ('A', 'C')
        """
        if a not in self._nodes or b not in self._nodes:
            raise KeyError("Source and target must be registered nodes")
        if a == b:
            return [a], 1.0, {"hop_count": 0, "total_distance_km": 0.0}

        graph = self._adjacency()
        cost: Dict[str, float] = {n: float("inf") for n in self._nodes}
        prev: Dict[str, Optional[str]] = {n: None for n in self._nodes}
        path_f: Dict[str, float] = {n: 0.0 for n in self._nodes}
        cost[a] = 0.0
        path_f[a] = 1.0
        heap: List[Tuple[float, str]] = [(0.0, a)]
        visited: Set[str] = set()

        while heap:
            cur_cost, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            if u == b:
                break
            for v, dist_km in graph.get(u, []):
                if v in visited:
                    continue
                eta = transmittance(dist_km)
                f_hop = max(0.25, min(1.0, eta))
                new_f = swap_fidelity_bell(path_f[u], f_hop)
                hop_cost = 1e-6 if eta <= 0 else cur_cost - math.log(eta) if eta > 0 else float("inf")
                if hop_cost < cost[v]:
                    cost[v] = hop_cost
                    prev[v] = u
                    path_f[v] = new_f
                    heapq.heappush(heap, (hop_cost, v))

        if prev.get(b) is None and a != b:
            return [], None, None

        # reconstruct
        path_rev: List[str] = []
        cur: Optional[str] = b
        while cur is not None:
            path_rev.append(cur)
            cur = prev[cur]
        path = list(reversed(path_rev))

        total_dist = sum(
            self.get_link(path[i], path[i + 1]).distance_km
            for i in range(len(path) - 1)
        )
        link_transmittances = [
            self.get_link(path[i], path[i + 1]).transmittance
            for i in range(len(path) - 1)
        ]

        # Accumulate end-to-end fidelity via Bell-corrected chain
        total_f = 1.0
        for i in range(len(path) - 1):
            link_obj = self.get_link(path[i], path[i + 1])
            total_f = swap_fidelity_bell(total_f, link_obj.fidelity)

        diagnostics = {
            "total_distance_km": total_dist,
            "hop_count": len(path) - 1,
            "link_transmittances": link_transmittances,
        }

        return path, total_f, diagnostics

    # ------------------------------------------------------------------
    # MST backbone builder
    # ------------------------------------------------------------------

    def build_backbone(self, min_population: int = 0) -> "QuantumNetwork":
        """
        Auto-connect all nodes above ``min_population`` into an MST backbone.

        Parameters
        ----------
        min_population : int, optional
            Population threshold (default 100 000).

        Returns
        -------
        QuantumNetwork
            A **new** network containing only backbone nodes and MST edges.
        """
        backbone_nodes = [n for n in self._nodes.values() if n.population >= min_population]
        if len(backbone_nodes) == 0:
            return QuantumNetwork(name=self.name + "_backbone")
        if len(backbone_nodes) == 1:
            result = QuantumNetwork(name=self.name + "_backbone")
            n = backbone_nodes[0]
            result.add_node(n.name, n.lat, n.lon, n.population, n.role)
            return result

        parent: Dict[str, str] = {n.name: n.name for n in backbone_nodes}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = find(parent[x])
                parent[x] = x
            return x

        def union(x: str, y: str) -> bool:
            rx, ry = find(x), find(y)
            if rx == ry:
                return False
            parent[ry] = rx
            return True

        edges: List[Tuple[float, str, str]] = []
        for na in backbone_nodes:
            for nb in backbone_nodes:
                if na.name >= nb.name:
                    continue
                d = haversine(na.lat, na.lon, nb.lat, nb.lon)
                edges.append((d, na.name, nb.name))
        edges.sort()

        result = QuantumNetwork(name=self.name + "_backbone")
        for n in backbone_nodes:
            result.add_node(n.name, n.lat, n.lon, n.population, n.role)

        added = 0
        for dist, na, nb in edges:
            if union(na, nb):
                result.add_link(na, nb)
                added += 1
                if added == len(backbone_nodes) - 1:
                    break

        return result

    # ------------------------------------------------------------------
    # Serialisation — JSON
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """
        Serialise the full network state to a JSON string.

        Returns
        -------
        str
            JSON-encoded network state.
        """
        return json.dumps(self._to_dict(), indent=indent)

    def save(self, path: str) -> None:
        """
        Save the full network state to a JSON file.

        Parameters
        ----------
        path : str
            Output file path.
        """
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    @classmethod
    def from_dict(cls, d: dict) -> "QuantumNetwork":
        """Reconstruct a network from a plain dict (as produced by ``_to_dict``)."""
        net = cls(name=d.get("name", "World"))
        for nd in d.get("nodes", []):
            net.add_node(
                name=nd["name"],
                lat=nd["lat"],
                lon=nd["lon"],
                population=nd.get("population", 0),
                role=NodeRole(nd.get("role", "endpoint")) if nd.get("role") else NodeRole.ENDPOINT,
            )
        for lnk in d.get("links", []):
            try:
                net.add_link(lnk["a"], lnk["b"], fidelity=lnk.get("fidelity", 1.0))
            except (KeyError, ValueError):
                pass  # skip malformed links
        net._current_time_seconds = d.get("current_time_seconds", 0.0)
        return net

    @classmethod
    def load(cls, path: str) -> "QuantumNetwork":
        """
        Load a network from a JSON file.

        Parameters
        ----------
        path : str
            Input file path.

        Returns
        -------
        QuantumNetwork
        """
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def _to_dict(self) -> dict:
        """Internal: produce a plain-dict representation."""
        return {
            "name": self.name,
            "version": "3.0.0",
            "current_time_seconds": self._current_time_seconds,
            "nodes": [
                {
                    "name": n.name,
                    "lat": n.lat,
                    "lon": n.lon,
                    "population": n.population,
                    "role": n.role.value,
                    "fidelity": n.fidelity,
                }
                for n in self._nodes.values()
            ],
            "links": [link.to_dict() for link in self._links.values()],
        }

    # ------------------------------------------------------------------
    # GeoJSON export
    # ------------------------------------------------------------------

    def to_geojson(self) -> dict:
        """
        Export the network topology as a GeoJSON FeatureCollection.

        Nodes become ``Feature`` points; links become ``Feature`` LineStrings.
        Link features include per-link fidelity, QBER, and key rate fields.

        Returns
        -------
        dict
            GeoJSON-serialisable dictionary.
        """
        features: List[dict] = []

        for node in self._nodes.values():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [node.lon, node.lat]},
                "properties": {
                    "name": node.name,
                    "population": node.population,
                    "role": node.role.value,
                    "is_repeater": node.is_repeater,
                },
            })

        for link in self._links.values():
            na = self._nodes[link.a]
            nb = self._nodes[link.b]
            skr, _ = secret_key_rate(link.fidelity, link.distance_km)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[na.lon, na.lat], [nb.lon, nb.lat]],
                },
                "properties": {
                    "distance_km": round(link.distance_km, 3),
                    "fidelity": round(link.fidelity, 6),
                    "qber": round(link.qber, 6),
                    "key_rate": round(skr, 4),
                    "active": link.active,
                },
            })

        return {"type": "FeatureCollection", "features": features}

    # ------------------------------------------------------------------
    # Time evolution
    # ------------------------------------------------------------------

    def advance_time(
        self,
        dt_seconds: float,
        use_t1_t2: bool = False,
    ) -> None:
        """
        Advance the network clock.

        All entangled links decohere toward the maximally-mixed state.

        Parameters
        ----------
        dt_seconds : float
            Elapsed physical time in seconds.
        use_t1_t2 : bool, optional
            If True, use the two-channel T1/T2 model. Otherwise use
            the single-channel T2 model (default False).
        """
        if dt_seconds <= 0:
            return
        self._current_time_seconds += dt_seconds
        for link in self._links.values():
            if link.active:
                link.age_seconds += dt_seconds
                if use_t1_t2:
                    link.fidelity = decohere_t1_t2(link.fidelity, dt_seconds)
                else:
                    link.fidelity = decohere(link.fidelity, dt_seconds)
                if link.fidelity <= 0.251:
                    link.active = False

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """One-line human-readable network summary."""
        active = sum(1 for link in self._links.values() if link.active)
        repeaters = sum(1 for n in self._nodes.values() if n.is_repeater)
        avg_f = (
            sum(link.fidelity for link in self._links.values())
            / max(1, len(self._links))
        )
        return (
            f"QuantumNetwork({self.name!r}): "
            f"{len(self._nodes)} nodes, {len(self._links)} links "
            f"({active} active), {repeaters} repeaters, "
            f"avg fidelity {avg_f:.3f}, t={self._current_time_seconds:.1f}s"
        )

    def __repr__(self) -> str:
        return self.summary()

    def __len__(self) -> int:
        return len(self._nodes)


# ---------------------------------------------------------------------------
# Backward-compatibility aliases (routing module removed)
# ---------------------------------------------------------------------------

def _dijkstra_shortest_path(graph: Dict, source: str, target: str) -> Optional[List[str]]:
    """Legacy Dijkstra helper (used by backward-compat aliases)."""
    if source == target:
        return [source]
    dist: Dict[str, float] = {n: float("inf") for n in graph}
    prev: Dict[str, Optional[str]] = {n: None for n in graph}
    dist[source] = 0.0
    heap: List[Tuple[float, str]] = [(0.0, source)]
    visited: Set[str] = set()
    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if u == target:
            break
        for v, w in graph.get(u, []):
            if v in visited:
                continue
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    if prev.get(target) is None:
        return None
    path: List[str] = []
    cur: Optional[str] = target
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


# Re-export load_csv as from_csv for backward compat
QuantumNetwork.from_csv = classmethod(lambda cls, path, **kw: (
    cls.from_dict({"nodes": load_csv(path, **kw)})
))
