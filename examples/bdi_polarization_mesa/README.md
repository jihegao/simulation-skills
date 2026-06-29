# BDI Recommendation Polarization

This case tests whether a BDI-style agent population can reproduce
polarization-like dynamics when agents receive recommendation-ranked content
and group actions feed new popular content back into the pool.

The model uses:

- belief: one-dimensional issue position from `-1` to `1`;
- desire: social fit and action thresholds;
- intention: `idle`, `support`, `share`, or `mobilize`;
- recommendation: similarity and popularity-weighted content selection;
- group action: sharing and mobilizing create new content with extra popularity;
- LLM sampling: before the batch run, the runner asks the local `opencode` CLI
  for a few BDI behavior profiles, validates numeric ranges, and caches them in
  the output directory. If `opencode` is unavailable, the run records the error
  and falls back to built-in profiles so tests remain reproducible.

Run:

```bash
python3 -m examples.bdi_polarization_mesa.run_experiment \
  --config examples/bdi_polarization_mesa/experiment.json \
  --output-dir outputs/bdi_polarization
python3 -m examples.bdi_polarization_mesa.static_viewer \
  --summary outputs/bdi_polarization/summary.json \
  --output outputs/bdi_polarization/viewer.html
```

Generate one seeded replay viewer:

```bash
python3 -m examples.bdi_polarization_mesa.single_run_viewer \
  --config examples/bdi_polarization_mesa/experiment.json \
  --output-dir outputs/bdi_polarization_single
python3 -m http.server 8766 --bind 127.0.0.1 \
  --directory outputs/bdi_polarization_single
```

The evidence boundary is the generated `run_rows.csv` and `summary.json`.
For the replay UI, the evidence boundary is `single_run_replay.json`.
This is an exploratory mechanism reproduction, not a calibrated social-media
or political-behavior model.
