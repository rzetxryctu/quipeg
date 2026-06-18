"""
Command-line interface for Quipeg v3.

Usage::

    quipeg info
    quipeg demo
    quipeg simulate --from London --to Tokyo
    quipeg render --output map.html
    quipeg export --format geojson --output network.geojson

Run ``quipeg --help`` for full usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from quipeg import __version__
from quipeg.network import QuantumNetwork, load_csv
from quipeg.physics import haversine, secret_key_rate, swap_fidelity_bell
from quipeg.render import save_html


# ---------------------------------------------------------------------------
# Demo network builder
# ---------------------------------------------------------------------------

def _build_demo_network() -> QuantumNetwork:
    """Create a small global network with real cities."""
    cities = [
        ("London",        51.5074,   -0.1278,  9_000_000, "backbone"),
        ("Paris",         48.8566,    2.3522,  2_100_000, "backbone"),
        ("Frankfurt",     50.1109,    8.6821,    700_000, "repeater"),
        ("Amsterdam",     52.3676,    4.9041,    850_000, "repeater"),
        ("Madrid",        40.4168,   -3.7038,  3_300_000, "repeater"),
        ("Warsaw",        52.2297,   21.0122,  1_700_000, "repeater"),
        ("Moscow",        55.7558,   37.6173,  7_000_000, "backbone"),
        ("Tokyo",         35.6762,  139.6503, 13_960_000, "backbone"),
        ("Singapore",      1.3521,  103.8198,  5_600_000, "repeater"),
        ("Sydney",       -33.8688,  151.2093,  4_800_000, "endpoint"),
        ("New York",      40.7128,  -74.0060,  8_300_000, "backbone"),
        ("Los Angeles",   34.0522, -118.2437,  3_800_000, "endpoint"),
        ("Chicago",       41.8781,  -87.6298,  2_700_000, "endpoint"),
        ("Miami",         25.7617,  -80.1918,  1_600_000, "endpoint"),
        ("Dubai",         25.2048,   55.2708,  1_500_000, "endpoint"),
    ]

    links = [
        ("London",        "Paris"),
        ("London",        "Amsterdam"),
        ("London",        "Frankfurt"),
        ("Paris",         "Frankfurt"),
        ("Paris",         "Madrid"),
        ("Frankfurt",     "Warsaw"),
        ("Warsaw",        "Moscow"),
        ("Madrid",        "Dubai"),
        ("Dubai",         "Singapore"),
        ("Singapore",     "Tokyo"),
        ("Singapore",     "Sydney"),
        ("Tokyo",         "Los Angeles"),
        ("Los Angeles",   "Chicago"),
        ("Los Angeles",   "New York"),
        ("Chicago",       "New York"),
        ("New York",      "Miami"),
        ("Miami",         "Los Angeles"),
    ]

    net = QuantumNetwork(name="Global QKD Backbone v3")
    for city, lat, lon, pop, role in cities:
        net.add_node(city, lat, lon, pop, role=role)
    for a, b in links:
        net.add_link(a, b)

    return net


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_demo(_args: argparse.Namespace) -> None:
    """Run the interactive demo."""
    print("=" * 60)
    print("  Quipeg v3 — Global Quantum Network Demo")
    print("=" * 60)
    net = _build_demo_network()
    print(f"\n{net.summary()}\n")

    # Node table
    print(f"{'City':<16} {'Lat':>8} {'Lon':>9} {'Pop (M)':>8} {'Role':>10}")
    print("-" * 58)
    for node in net.nodes():
        pop_m = node.population / 1e6
        print(f"{node.name:<16} {node.lat:>8.4f} {node.lon:>9.4f} "
              f"{pop_m:>8.2f} {node.role.value:>10}")

    # Link table
    print(f"\n{'Link':<35} {'Dist km':>10} {'Fidelity':>9} {'QBER':>7} {'SKR Mbit/s':>12}")
    print("-" * 78)
    for link in net.links():
        label = f"{link.a} ↔ {link.b}"
        skr, _ = secret_key_rate(link.fidelity, link.distance_km)
        print(f"{label:<35} {link.distance_km:>10.1f} {link.fidelity:>9.4f} "
              f"{link.qber:>7.5f} {skr/1e6:>12.3f}")

    # Shortest path: London → Tokyo
    print("\n── Shortest path (km): London → Tokyo")
    sp = net.shortest_path("London", "Tokyo")
    if sp:
        for i, name in enumerate(sp):
            node = net.get_node(name)
            marker = " ★" if node.is_repeater else ""
            print(f"  {i+1:>2}. {name}{marker}")
        total_dist = sum(
            net.get_link(sp[i], sp[i+1]).distance_km
            for i in range(len(sp) - 1)
        )
        print(f"  Total distance: {total_dist:.0f} km")

    # End-to-end fidelity: London → Tokyo
    print("\n── End-to-end fidelity (Bell-corrected): London → Tokyo")
    f_e2e, skr, diag = net.end_to_end("London", "Tokyo")
    print(f"  End-to-end fidelity: {f_e2e:.4f}")
    print(f"  Estimated SKR: {skr/1e6:.2f} Mbit/s")
    print(f"  Hops: {diag['hop_count']}")

    # SKR table for London → Paris
    print("\n── BB84 SKR vs fidelity: London → Paris")
    d_lp = haversine(51.5074, -0.1278, 48.8566, 2.3522)
    print(f"{'Fidelity':>10} {'QBER':>8} {'Transmittance':>14} {'SKR Mbit/s':>12}")
    print("-" * 47)
    for fidelity in [1.0, 0.97, 0.95, 0.90, 0.80]:
        skr2, info = secret_key_rate(fidelity, d_lp)
        print(f"{fidelity:>10.2f} {info['qber']:>8.4f} "
              f"{info['transmittance']:>14.5f} {skr2/1e6:>12.3f}")

    # Bell-corrected vs arithmetic swap comparison
    print("\n── Swap fidelity: Bell-corrected vs arithmetic mean (v2.0)")
    print(f"{'F1':>6} {'F2':>6} {'F_bell':>8} {'F_avg':>8} {'Diff':>8}")
    print("-" * 40)
    for f1, f2 in [(0.95, 0.95), (0.90, 0.90), (0.80, 0.80), (0.50, 0.50)]:
        f_bell = swap_fidelity_bell(f1, f2)
        f_avg = (f1 + f2) / 2
        print(f"{f1:>6.2f} {f2:>6.2f} {f_bell:>8.4f} {f_avg:>8.4f} {f_bell-f_avg:>+8.4f}")

    print("\n✓ Demo complete.")


def cmd_info(_args: argparse.Namespace) -> None:
    """Print package and version information."""
    print(f"Quipeg v{__version__}")
    print("Planetary Quantum Communication Backbone Simulator")
    print()
    print("  Physics: Haversine, fibre loss, decoherence, T1/T2,")
    print("           Bell-corrected swap, DEJMPS purification, BB84 SKR")
    print("  Network: QuantumNode, QuantumLink, QuantumNetwork")
    print("  Routing: Dijkstra shortest path, fidelity-aware path")
    print("  Render:  Standalone SVG/JS HTML map")
    print("  Serial:  JSON save/load, GeoJSON export")
    print()
    print("  License: Apache 2.0")
    print(f"  Python:  {sys.version.split()[0]}+")


def cmd_simulate(args: argparse.Namespace) -> None:
    """Simulate path fidelity between two nodes."""
    # Load network from CSV if provided, otherwise build demo
    if args.network:
        try:
            raw_nodes = load_csv(args.network)
        except FileNotFoundError:
            sys.stderr.write(f"Error: file not found: {args.network}\n")
            sys.exit(1)

        net = QuantumNetwork(name="Custom Network")
        for nd in raw_nodes:
            net.add_node(nd.name, nd.lat, nd.lon, nd.population, nd.role)
        # Add default links between all nodes
        names = [n.name for n in raw_nodes]
        for i in range(len(names) - 1):
            net.add_link(names[i], names[i + 1])
    else:
        net = _build_demo_network()

    src = args.from_
    dst = args.to

    if src not in net.node_names():
        sys.stderr.write(f"Error: source node {src!r} not found.\n")
        sys.exit(1)
    if dst not in net.node_names():
        sys.stderr.write(f"Error: destination node {dst!r} not found.\n")
        sys.exit(1)

    path = net.shortest_path(src, dst)
    if not path:
        sys.stderr.write(f"No path found between {src!r} and {dst!r}.\n")
        sys.exit(1)

    f_e2e, skr, diag = net.end_to_end(src, dst)

    print(f"Simulate: {src} → {dst}")
    print(f"  Path: {' → '.join(path)}")
    print(f"  Hops: {diag['hop_count']}")
    print(f"  Total distance: {diag['total_distance_km']:.1f} km")
    print(f"  End-to-end fidelity (Bell-corrected): {f_e2e:.6f}")
    print(f"  Estimated SKR: {skr/1e6:.4f} Mbit/s")
    print()
    print(f"  {'Link':<30} {'Dist km':>9} {'Fidelity':>10} {'QBER':>8} {'SKR Mbit/s':>12}")
    print("  " + "-" * 72)
    for detail in diag["link_details"]:
        skr_val = detail["skr"] / 1e6
        print(f"  {detail['link']:<30} {detail['distance_km']:>9.1f} "
              f"{detail['fidelity']:>10.6f} {detail['qber']:>8.5f} "
              f"{skr_val:>12.4f}")


def cmd_render(args: argparse.Namespace) -> None:
    """Export the network as an interactive HTML map."""
    if args.network:
        try:
            raw_nodes = load_csv(args.network)
        except FileNotFoundError:
            sys.stderr.write(f"Error: file not found: {args.network}\n")
            sys.exit(1)

        net = QuantumNetwork(name="Custom Network")
        for nd in raw_nodes:
            net.add_node(nd.name, nd.lat, nd.lon, nd.population, nd.role)
        names = [n.name for n in raw_nodes]
        for i in range(len(names) - 1):
            net.add_link(names[i], names[i + 1])
    else:
        net = _build_demo_network()

    output_path = args.output or "network_map.html"
    title = args.title or f"Quipeg v{__version__} — {net.name}"

    save_html(net, output_path, title=title)
    print(f"Saved HTML map → {output_path}")
    print(f"  {net.node_count()} nodes, {net.link_count()} links")


def cmd_export(args: argparse.Namespace) -> None:
    """Export the network as GeoJSON or JSON."""
    if args.network:
        try:
            raw_nodes = load_csv(args.network)
        except FileNotFoundError:
            sys.stderr.write(f"Error: file not found: {args.network}\n")
            sys.exit(1)

        net = QuantumNetwork(name="Custom Network")
        for nd in raw_nodes:
            net.add_node(nd.name, nd.lat, nd.lon, nd.population, nd.role)
        names = [n.name for n in raw_nodes]
        for i in range(len(names) - 1):
            net.add_link(names[i], names[i + 1])
    else:
        net = _build_demo_network()

    output_path = args.output or (
        "network.geojson" if args.format == "geojson" else "network.json"
    )

    if args.format == "geojson":
        data = net.to_geojson()
    else:
        data = net._to_dict()

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    print(f"Exported ({args.format}) → {output_path}")
    print(f"  {net.node_count()} nodes, {net.link_count()} links")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point, exposed as the ``quipeg`` console script.

    Parameters
    ----------
    argv : list of str, optional
        Override sys.argv (useful for testing).

    Returns
    -------
    int
        Exit code (0 = success).
    """
    parser = argparse.ArgumentParser(
        prog="quipeg",
        description=(
            f"Quipeg v{__version__} — "
            "Planetary Quantum Communication Backbone Simulator"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  quipeg info\n"
            "  quipeg demo\n"
            "  quipeg simulate --from London --to Tokyo\n"
            "  quipeg render --output map.html\n"
            "  quipeg export --format geojson --output network.geojson\n"
        ),
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(required=True, dest="command")

    # info
    p_info = sub.add_parser("info", help="Show package info and version")
    p_info.set_defaults(func=cmd_info)

    # demo
    p_demo = sub.add_parser("demo", help="Run the interactive demo (no file needed)")
    p_demo.set_defaults(func=cmd_demo)

    # simulate
    p_sim = sub.add_parser(
        "simulate",
        help="Simulate path fidelity between two nodes",
    )
    p_sim.add_argument("--from", dest="from_", required=True, help="Source node name")
    p_sim.add_argument("--to", dest="to", required=True, help="Destination node name")
    p_sim.add_argument(
        "--network", default=None,
        help="CSV file with network nodes (optional; uses demo network if omitted)",
    )
    p_sim.set_defaults(func=cmd_simulate)

    # render
    p_render = sub.add_parser("render", help="Export network as interactive HTML map")
    p_render.add_argument(
        "--output", "-o", default=None,
        help="Output HTML file path (default: network_map.html)",
    )
    p_render.add_argument(
        "--network", default=None,
        help="CSV file with network nodes (optional)",
    )
    p_render.add_argument(
        "--title", default=None,
        help="Page title override",
    )
    p_render.set_defaults(func=cmd_render)

    # export
    p_exp = sub.add_parser(
        "export",
        help="Export network as GeoJSON or JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Formats: geojson, json",
    )
    p_exp.add_argument(
        "--format", "-f",
        choices=["geojson", "json"],
        default="geojson",
        help="Output format (default: geojson)",
    )
    p_exp.add_argument(
        "--output", "-o", default=None,
        help="Output file path",
    )
    p_exp.add_argument(
        "--network", default=None,
        help="CSV file with network nodes (optional)",
    )
    p_exp.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
