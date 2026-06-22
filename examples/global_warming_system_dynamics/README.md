# Global Warming System Dynamics

This case models global warming as a compact system-dynamics stock-flow model:

- atmospheric CO2 is the main stock;
- annual emissions are the inflow;
- land/ocean uptake is the balancing outflow;
- radiative forcing links CO2 stock to equilibrium warming;
- surface temperature is a delayed response stock.

The generated page visualizes both the forecast paths and the SD model
structure. It includes stock-flow links, feedback-loop labels, current equation
readouts, and checkpoint predictions for 2030, 2035, and 2040.

Generate the self-contained page:

```bash
python3 -m examples.global_warming_system_dynamics.app \
  --output examples/global_warming_system_dynamics/index.html
```

Open:

```text
examples/global_warming_system_dynamics/index.html
```

Default scenarios:

- `rapid`: rapid emissions decline with improving non-CO2 forcing.
- `baseline`: slow transition path.
- `high`: continuing high emissions and rising non-CO2 forcing.

Default short- and medium-term baseline checkpoints:

| Year | Temperature anomaly | CO2 concentration | Emissions |
| --- | ---: | ---: | ---: |
| 2030 | about 1.43 C | about 437 ppm | about 41.2 GtCO2/year |
| 2035 | about 1.52 C | about 449 ppm | about 40.1 GtCO2/year |
| 2040 | about 1.62 C | about 461 ppm | about 39.1 GtCO2/year |

Evidence boundary: this case supports scenario comparison and threshold-risk
checks under explicit assumptions. It does not model ENSO, regional climate,
ice-sheet dynamics, aerosol chemistry, extreme-weather frequency, or full
Earth-system feedbacks.

