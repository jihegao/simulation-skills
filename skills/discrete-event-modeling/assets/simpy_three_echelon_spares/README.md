# SimPy Three-Echelon Spare-Part Logistics

Models a three-echelon spare-part support chain for a 30-day service-level estimate.

The encoded support points are:

- Base support point: 10 spare parts, no higher-echelon replenishment.
- Relay support point: 1 spare part, replenished from base with a 48 hour transport time.
- Local support point: 1 spare part, replenished from relay with a 10 hour transport time.

Demand arrivals are a Poisson process represented by exponentially distributed interarrival times with a 24 hour mean. A demand is counted as satisfied only when the local support point has an on-hand part at the instant of demand. When local stock is consumed, the model requests a one-for-one replenishment from relay; relay consumption triggers a one-for-one replenishment from base while base stock remains available.

Run the bundled experiment:

```bash
python3 discrete-event-modeling/scripts/run_simpy_experiment.py \
  --model discrete-event-modeling/assets/simpy_three_echelon_spares/model.py \
  --config discrete-event-modeling/assets/simpy_three_echelon_spares/experiment.json \
  --output-dir /tmp/three-echelon-spares-results \
  --install-dir /tmp/des-simpy-env
```

The primary metric is `service_level`, the fraction of demands immediately satisfied by local on-hand stock during the 720 hour evaluation horizon.
