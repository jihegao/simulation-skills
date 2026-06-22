# 火柴棍桥梁物理仿真

This example builds a simplified matchstick Warren-truss bridge and evaluates
whether it can carry point loads without exceeding member, glued-joint, or
deflection limits.

The core model is a quasi-static structural envelope:

- nodes define deck, top chord, and support positions;
- matchstick members define chords, diagonals, verticals, and cross ties;
- load cases estimate chord force, diagonal shear, joint reaction, and midspan
  deflection;
- the verdict is `holds_load` only when every utilization stays within limit.

Run the sweep:

```bash
python3 examples/biped_microgravity/run_experiment.py
```

Write the browser viewer:

```bash
python3 examples/biped_microgravity/static_viewer.py
```

Open `outputs/biped_microgravity/viewer.html` to inspect the bridge structure,
load arrow, member layout, utilization metrics, and failure modes.

This is a behavioral demonstration, not a finite-element solver. Results
describe the simplified structural assumptions in this example and do not prove
the capacity of a real bridge.
