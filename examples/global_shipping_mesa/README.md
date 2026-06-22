# Global Shipping Mesa/SimPy

This example models a small global container-shipping market with about ten
major ports. Orders are generated as random origin/destination pairs. Idle ships
claim the open order whose origin port is nearest to their current position.

The model combines two layers:

- Mesa provides the model shell, seeded runs, snapshots, and state export.
- SimPy drives ship processes and port calls. Each port has berth and crane
  resources; yard space pressure slows load/unload handling.

The embedded GIS layer is intentionally compact: port latitude/longitude points
are stored in `model.py`, and sailing distance uses great-circle nautical miles.

Run an experiment:

```bash
python -m examples.global_shipping_mesa.run_experiment \
  --config examples/global_shipping_mesa/experiment.json \
  --output-dir outputs/global_shipping
```

Generate the 3D globe viewer:

```bash
python -m examples.global_shipping_mesa.static_viewer \
  --output outputs/global_shipping/index.html
```

Then serve the output directory:

```bash
python3 -m http.server 8765 --directory outputs/global_shipping
```

Open `http://127.0.0.1:8765/`. The viewer uses CesiumJS with NaturalEarth
imagery, draggable globe navigation, and daylight lighting. If
`cesium/Build/Cesium/Cesium.js` exists next to the generated `index.html`, the
viewer uses that local runtime; otherwise it falls back to the CesiumJS CDN.

Evidence boundary: the CSV and JSON written by the experiment runner support
capacity/queue comparisons. The 3D globe is an inspection surface, not a proof
of operational validity.
