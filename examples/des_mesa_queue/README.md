# Mesa DES Queue Example

This example wraps a SimPy discrete-event queue in a Mesa model so the same
simulation can be inspected through Solara and run as a repeatable batch
experiment.

- `model.py`: SimPy arrival, patience, service, and resource contention logic
  exposed through a Mesa `Model` with `step()`, `snapshot()`, and
  `visualization_state()`.
- `app.py`: Solara dashboard that shows arrivals, the waiting queue, service
  servers, recent completions, and event logs.
- `run_experiment.py`: batch runner for seed and parameter sweeps.
- `experiment.json`: default capacity sweep over server count.

Run the experiment:

```bash
python -m examples.des_mesa_queue.run_experiment \
  --config examples/des_mesa_queue/experiment.json \
  --output-dir outputs/des_mesa_queue
```

Run the visualization:

```bash
solara run examples/des_mesa_queue/app.py --host 127.0.0.1 --port 8765
```

The evidence boundary is the CSV and JSON written by the runner. The Solara page
is for inspection and debugging of the event flow.

