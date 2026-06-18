"""
render — Interactive HTML topology visualizer.

Exports a QuantumNetwork as a fully standalone HTML file with an inline
SVG map and JavaScript tooltip system. Zero external dependencies —
works completely offline.

The generated HTML contains no CDN links, no external fonts, and no
external image assets. It can be opened in any modern browser directly
from the filesystem.
"""

from quipeg.network import QuantumNetwork


# ---------------------------------------------------------------------------
# SVG / HTML renderer
# ---------------------------------------------------------------------------

def _lon_lat_to_svg(
    nodes: list,
    width: int = 960,
    height: int = 500,
    padding: float = 40.0,
) -> dict:
    """
    Project lon/lat coordinates onto an SVG viewBox using a simple
    equirectangular projection with automatic viewport scaling.

    Parameters
    ----------
    nodes : list of QuantumNode
    width, height : int
        SVG viewport dimensions.
    padding : float
        Minimum margin from viewport edges.

    Returns
    -------
    dict
        {
            "lon_to_x": callable,
            "lat_to_y": callable,
            "lon_range": (min_lon, max_lon),
            "lat_range": (min_lat, max_lat),
        }
    """
    if not nodes:
        return {
            "lon_to_x": lambda l: width / 2,
            "lat_to_y": lambda l: height / 2,
            "lon_range": (0.0, 1.0),
            "lat_range": (0.0, 1.0),
        }

    lons = [n.lon for n in nodes]
    lats = [n.lat for n in nodes]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Avoid division by zero if all nodes have same coordinate
    lon_range = max(max_lon - min_lon, 1e-6)
    lat_range = max(max_lat - min_lat, 1e-6)

    # Equirectangular projection
    # Add padding
    svg_w = width - 2 * padding
    svg_h = height - 2 * padding

    def lon_to_x(lon: float) -> float:
        return padding + (lon - min_lon) / lon_range * svg_w

    def lat_to_y(lat: float) -> float:
        # y increases downward in SVG; flip latitude
        return padding + (max_lat - lat) / lat_range * svg_h

    return {
        "lon_to_x": lon_to_x,
        "lat_to_y": lat_to_y,
        "lon_range": (min_lon, max_lon),
        "lat_range": (min_lat, max_lat),
    }


def _node_color(role: str) -> str:
    """SVG fill colour for a node based on its role."""
    return {
        "endpoint": "#4a90e2",
        "repeater": "#e67e22",
        "backbone": "#27ae60",
    }.get(role, "#95a5a6")


def to_html(
    network: QuantumNetwork,
    *,
    title: str = "Quipeg v3 — Quantum Network Map",
    width: int = 960,
    height: int = 500,
    padding: float = 60.0,
) -> str:
    """
    Render a QuantumNetwork as a standalone interactive HTML string.

    The output is a self-contained HTML5 document containing:
    - An SVG map of the network topology
    - Nodes rendered as circles (colour-coded by role)
    - Links rendered as lines (colour-coded by fidelity)
    - Hover tooltips showing node/link metrics
    - A legend and summary panel

    No external network requests are made. Works fully offline.

    Parameters
    ----------
    network : QuantumNetwork
        The network to render.
    title : str, optional
        Page title (default "Quipeg v3 — Quantum Network Map").
    width, height : int, optional
        SVG viewport dimensions (default 960×500).
    padding : float, optional
        Viewport padding in pixels (default 60).

    Returns
    -------
    str
        A complete HTML document as a Unicode string.

    Examples
    --------
    >>> net = QuantumNetwork("Test")
    >>> net.add_node("A", 0, 0, role="endpoint")
    >>> net.add_node("B", 1, 1, role="repeater")
    >>> net.add_link("A", "B")
    >>> html = to_html(net)
    >>> "<svg" in html
    True
    >>> "<title>" in html
    True
    """
    nodes = network.nodes()
    links = network.links()

    proj = _lon_lat_to_svg(nodes, width, height, padding)
    lon_to_x = proj["lon_to_x"]
    lat_to_y = proj["lat_to_y"]

    # ---- SVG link lines ----
    link_elements: List[str] = []
    for link in links:
        x1 = lon_to_x(network.get_node(link.a).lon)
        y1 = lat_to_y(network.get_node(link.a).lat)
        x2 = lon_to_x(network.get_node(link.b).lon)
        y2 = lat_to_y(network.get_node(link.b).lat)

        # Colour by fidelity: green (high) → red (low)
        f = link.fidelity
        # Map fidelity [0.25, 1.0] to hue [0°, 120°]
        hue = (f - 0.25) / 0.75 * 120.0
        # SVG hsl: hsl(hue, 70%, 45%)
        stroke = f"hsl({hue:.1f}, 70%, 45%)"
        stroke_opacity = 0.9 if link.active else 0.3

        # Compute SVG line length for tooltip
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        tooltip_id = f"tooltip_{link.a}_{link.b}".replace(" ", "_").replace("-", "_")

        tooltip_data = (
            f"Link: {link.a} ↔ {link.b}"
            f"\\nDistance: {link.distance_km:.1f} km"
            f"\\nFidelity: {link.fidelity:.4f}"
            f"\\nQBER: {link.qber:.5f}"
            f"\\nKey Rate: {link.key_rate/1e6:.3f} Mbit/s"
            f"\\nStatus: {'Active' if link.active else 'Inactive'}"
        )

        link_elements.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="2" '
            f'stroke-opacity="{stroke_opacity}" '
            f'class="link" '
            f'data-tooltip-id="{tooltip_id}" '
            f'cursor="pointer" />'
        )
        # Tooltip element for this link
        link_elements.append(
            f'<g id="{tooltip_id}" class="tooltip-group" visibility="hidden">'
            f'<rect x="{mx - 75:.1f}" y="{my - 52:.1f}" width="150" height="50" '
            f'rx="4" fill="#2c3e50" fill-opacity="0.95" />'
            f'<text x="{mx:.1f}" y="{my - 34:.1f}" text-anchor="middle" '
            f'fill="white" font-size="10" font-family="monospace">'
            f'{link.a} ↔ {link.b}'
            f'</text>'
            f'<text x="{mx:.1f}" y="{my - 20:.1f}" text-anchor="middle" '
            f'fill="#aaaaff" font-size="9" font-family="monospace">'
            f'F={link.fidelity:.3f} QBER={link.qber:.4f}'
            f'</text>'
            f'<text x="{mx:.1f}" y="{my - 8:.1f}" text-anchor="middle" '
            f'fill="#aaaaff" font-size="9" font-family="monospace">'
            f'SKR={link.key_rate/1e6:.3f} Mbit/s'
            f'</text>'
            f'</g>'
        )

    # ---- SVG node circles ----
    node_elements: List[str] = []
    for node in nodes:
        cx = lon_to_x(node.lon)
        cy = lat_to_y(node.lat)
        color = _node_color(node.role.value)
        r = 8 if node.is_repeater else 6
        tooltip_id = f"n_{node.name}".replace(" ", "_").replace("-", "_")

        tooltip_lines = [
            f"Node: {node.name}",
            f"Role: {node.role.value}",
            f"Lat: {node.lat:.4f}  Lon: {node.lon:.4f}",
            f"Population: {node.population:,}",
            f"Fidelity: {node.fidelity:.4f}",
            f"Neighbors: {len(network.neighbors(node.name))}",
        ]

        # Build tooltip with word-wrap (max 25 chars per line)
        def wrap(text: str, width: int = 22) -> List[str]:
            words = text.split()
            lines, cur = [], ""
            for w in words:
                if len(cur) + len(w) + 1 <= width:
                    cur = (cur + " " + w).strip()
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            return lines

        wrapped = []
        for line in tooltip_lines:
            wrapped.extend(wrap(line))

        num_lines = len(wrapped)
        tt_h = 14 * num_lines + 10
        tt_w = 160

        node_elements.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" '
            f'fill="{color}" stroke="#fff" stroke-width="1.5" '
            f'class="node" data-tooltip-id="{tooltip_id}" '
            f'cursor="pointer" />'
        )
        node_elements.append(
            f'<text x="{cx:.1f}" y="{cy + r + 14:.1f}" '
            f'text-anchor="middle" fill="#2c3e50" '
            f'font-size="11" font-family="sans-serif" font-weight="600" '
            f'pointer-events="none">{node.name}</text>'
        )
        # Tooltip element
        ty = cy - r - 4
        node_elements.append(
            f'<g id="{tooltip_id}" class="tooltip-group" visibility="hidden">'
            f'<rect x="{cx - tt_w//2:.1f}" y="{ty - tt_h:.1f}" '
            f'width="{tt_w}" height="{tt_h:.1f}" '
            f'rx="4" fill="#2c3e50" fill-opacity="0.95" />'
        )
        for i, line in enumerate(wrapped):
            node_elements.append(
                f'<text x="{cx:.1f}" y="{ty - tt_h + 12 + i * 14:.1f}" '
                f'text-anchor="middle" fill="white" '
                f'font-size="10" font-family="monospace">{line}</text>'
            )
        node_elements.append('</g>')

    # ---- Legend ----
    legend_items = [
        ("#4a90e2", "Endpoint"),
        ("#e67e22", "Repeater"),
        ("#27ae60", "Backbone"),
    ]
    fidelity_gradient = (
        '<defs>'
        '<linearGradient id="fidelityGrad" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="hsl(0,70%,45%)" />'
        '<stop offset="50%" stop-color="hsl(60,70%,45%)" />'
        '<stop offset="100%" stop-color="hsl(120,70%,45%)" />'
        '</linearGradient>'
        '</defs>'
    )

    legend_y = height - 38
    legend_elements = [
        f'<rect x="10" y="{legend_y - 5}" width="940" height="36" rx="6" '
        f'fill="#f8f9fa" stroke="#dee2e6" stroke-width="1" />',
        '<text x="20" y="' + str(legend_y + 14) + '" '
        'fill="#2c3e50" font-size="11" font-family="sans-serif">'
        '● Node:</text>',
    ]
    for i, (color, label) in enumerate(legend_items):
        lx = 85 + i * 80
        legend_elements.append(
            f'<circle cx="{lx}" cy="{legend_y + 8}" r="5" fill="{color}" stroke="#fff" />'
            f'<text x="{lx + 9}" y="{legend_y + 12}" '
            f'fill="#2c3e50" font-size="10" font-family="sans-serif">{label}</text>'
        )
    # Fidelity gradient
    gx = 330
    legend_elements.append(
        f'<text x="{gx}" y="{legend_y + 12}" fill="#2c3e50" '
        'font-size="10" font-family="sans-serif">Fidelity:</text>'
    )
    legend_elements.append(
        f'<rect x="{gx + 55}" y="{legend_y + 1}" width="100" height="12" '
        'fill="url(#fidelityGrad)" rx="3" />'
    )
    legend_elements.append(
        f'<text x="{gx + 55}" y="{legend_y + 22}" fill="#555" '
        'font-size="9" font-family="monospace">0.25</text>'
    )
    legend_elements.append(
        f'<text x="{gx + 148}" y="{legend_y + 22}" fill="#555" '
        'font-size="9" font-family="monospace" text-anchor="end">1.0</text>'
    )
    # Info
    legend_elements.append(
        f'<text x="840" y="{legend_y + 14}" fill="#7f8c8d" '
        'font-size="10" font-family="sans-serif" text-anchor="end">'
        f'{network.node_count()} nodes · {network.link_count()} links</text>'
    )

    # ---- Hover interaction script ----
    script = """
    <script type="text/javascript">
    // <![CDATA[
    (function() {
        var active = null;
        var groups = document.querySelectorAll('.tooltip-group');

        function show(id) {
            groups.forEach(function(g) {
                g.setAttribute('visibility', g.id === id ? 'visible' : 'hidden');
            });
        }
        function hide() {
            groups.forEach(function(g) { g.setAttribute('visibility', 'hidden'); });
        }

        document.querySelectorAll('.node, .link').forEach(function(el) {
            var tid = el.getAttribute('data-tooltip-id');
            el.addEventListener('mouseenter', function() { show(tid); });
            el.addEventListener('mouseleave', function() { hide(); });
        });
    })();
    // ]]>
    </script>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width={width}, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: #f0f2f5;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
    }}
    h1 {{
      font-size: 1.2rem;
      font-weight: 700;
      color: #2c3e50;
      margin-bottom: 10px;
      letter-spacing: -0.02em;
    }}
    .subtitle {{
      font-size: 0.82rem;
      color: #7f8c8d;
      margin-bottom: 14px;
    }}
    #map {{
      background: #eaf4fb;
      border: 1px solid #cfd8dc;
      border-radius: 10px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
      max-width: 100%;
    }}
    .node {{ transition: r 0.15s; }}
    .node:hover {{ r: 10; stroke: #2c3e50; stroke-width: 2; }}
    .link {{ transition: stroke-opacity 0.15s; }}
    .link:hover {{ stroke-opacity: 1 !important; stroke-width: 3; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p class="subtitle">{network.summary()}</p>
  <svg id="map" width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    {fidelity_gradient}
    {''.join(link_elements)}
    {''.join(node_elements)}
    {''.join(legend_elements)}
  </svg>
  {script}
</body>
</html>"""
    return html


def save_html(network: QuantumNetwork, path: str, **kwargs) -> None:
    """
    Render a network as HTML and save to a file.

    Parameters
    ----------
    network : QuantumNetwork
        Network to render.
    path : str
        Output HTML file path.
    **kwargs
        Forwarded to :func:`to_html`.
    """
    content = to_html(network, **kwargs)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# Required import for type hints
# ---------------------------------------------------------------------------
from typing import List
