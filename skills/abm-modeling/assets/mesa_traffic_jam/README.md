# Mesa Signalized Intersection Model

This asset models traffic on a toroidal grid with one horizontal road and one
vertical road crossing at the center. Horizontal cars move only left-to-right;
vertical cars move only top-to-bottom. The top/bottom and left/right edges wrap,
so cars leaving one edge re-enter from the opposite edge.

## Agents

- `IntersectionCarAgent`: position plus fixed direction, either east or south.
- `IntersectionTrafficModel`: synchronous single-cell movement with a fixed
  traffic light at the central intersection.

## Rule Order

1. Compute each car's next cell on the toroidal road.
2. Block movement into occupied or already-reserved cells.
3. Block entry into the center intersection unless that direction has green.
4. Optionally apply random slowdowns.
5. Move all accepted cars simultaneously.

The `horizontal_green`, `vertical_green`, `light_phase`, and `phase_step`
snapshot fields report the signal state used for the just-completed movement
step. In the initial `step = 0` snapshot, they report the starting signal state.

## Experiments

- `smoke.json`: one deterministic fixed-signal run for a quick contract check.
- `experiment.json`: load sweep over horizontal and vertical car counts.

Run from the repository root:

```bash
python3 abm-modeling/scripts/run_mesa_experiment.py \
  --model abm-modeling/assets/mesa_traffic_jam/model.py \
  --config abm-modeling/assets/mesa_traffic_jam/experiment.json \
  --output-dir outputs/traffic_intersection_load_sweep \
  --install-dir .abm-mesa-env
```

Interpret results as behavior of this rule set, not as calibrated roadway
forecasting.
