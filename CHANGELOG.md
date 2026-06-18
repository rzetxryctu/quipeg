# Changelog

All notable changes to Quipeg are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [3.0.0] — 2025-06-18

### Added
- **`swap_fidelity_bell()`** in `physics.py`: Bell-corrected product formula
  `F₁·F₂ + (1-F₁)(1-F₂)/3` replaces the arithmetic mean. Correctly accounts
  for Werner-state structure of Bell-state noise.
- **`dejmps_purify()`** in `physics.py`: Simplified DEJMPS purification protocol
  returning `(success, new_fidelity, success_prob)`.
- **`decohere_t1_t2()`** in `physics.py`: Two-channel decoherence separating
  energy relaxation (T1) and phase dephasing (T2) for more realistic memory
  modelling across qubit technologies.
- **`qber_from_fidelity()`** and **`secret_key_rate()`** in `physics.py`:
  Standalone QBER and BB84 SKR functions.
- **`render.py`**: New module with `to_html()` and `save_html()` producing a
  fully standalone SVG+JS interactive HTML map with hover tooltips.
- **`save()` / `load()`** on `QuantumNetwork`: Persist and restore full network
  state (nodes, links, fidelity, age, active flags) to/from JSON.
- **`to_geojson()`** extended: Link features now include `fidelity`, `qber`,
  and `key_rate` fields.
- **`end_to_end()`** on `QuantumNetwork`: Computes end-to-end fidelity and
  SKR estimate along a path using Bell-corrected swapping.
- **`shortest_path()`** moved into `QuantumNetwork` (Dijkstra implemented directly).
- **`render` subcommand** in CLI: Export HTML interactive map.
- **`export` subcommand** in CLI: Export GeoJSON or JSON.
- **`simulate` subcommand** in CLI: Run path fidelity simulation with diagnostics.

### Changed
- **`swap_fidelity()`** in `physics.py`: Now calls the Bell-corrected
  `swap_fidelity_bell()` internally. The arithmetic-mean formula from v2.0
  is preserved as `swap_fidelity_avg()`.
- **`EntanglementSwapping.swap()`**: Now uses Bell-corrected fidelity.
- **`EntanglementSwapping.swap_chain()`**: Uses Bell-corrected fidelity internally.

### Removed
- `routing.py`: Consolidates into `network.py` (Dijkstra is now a method on
  `QuantumNetwork`). Import paths from `quipeg.routing` are preserved as
  aliases for backward compatibility but are considered deprecated.
- `csv.DictReader` CSV I/O is now a free function (`load_csv`) rather than a
  classmethod; `QuantumNetwork.from_csv()` remains as a re-exported alias.

### Fixed
- `fidelity_path` was incorrectly using log on an empty transmittance value
  for zero-distance links.

---

## [2.0.0] — 2024-01-01

### Added
- `QuantumNetwork` with `add_node`, `add_link`, graph traversal methods.
- `QuantumRepeater` with entanglement memory buffers and swap/purify.
- `EntanglementSwapping` utility class.
- Haversine distance, fibre loss (dB), transmittance model.
- `decohere()` with single T2 exponential model.
- `qber_from_fidelity()`, `skr_bb84()` BB84 secret key rate.
- `swap_fidelity()` (arithmetic mean model).
- `shortest_path` and `fidelity_path` in `routing.py`.
- `build_backbone()` (MST auto-connect from CSV population data).
- CSV loader via `from_csv()`.
- GeoJSON export via `to_geojson()`.
- CLI with `demo`, `build`, `path`, `info` subcommands.
- Pytest test suite (~50 tests).
- GitHub Actions CI on Python 3.9–3.12.

### Changed
- Package renamed from `qnet` to `quipeg`.
- Python minimum version raised to 3.9.

---

## [1.0.0] — 2023-06-01

### Added
- Initial release: core physics functions and a simple network graph class.
- Haversine, transmittance, basic fidelity model.
- Alpha version — API subject to change.
