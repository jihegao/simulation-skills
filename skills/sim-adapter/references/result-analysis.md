# Result Analysis

Analyze simulation results as evidence under assumptions, not as direct truth about the world.

## Required Interpretation

Every result explanation should include:

- experiment question
- method used
- baseline and interventions
- parameters varied
- runs, seeds, horizon, and warm-up if applicable
- primary metric trend with raw values or summary values
- uncertainty or run-to-run variation
- mechanism that explains the trend
- assumptions and exclusions
- what the result does not prove

## Evidence Language

Use bounded language:

- "Under these assumptions, the model suggests..."
- "The simulated mechanism is..."
- "The result is sensitive to..."
- "This supports comparing scenarios, not a precise forecast."

Avoid:

- "This proves..."
- "The real system will..."
- "The optimal answer is..." unless optimization was explicitly modeled and validated

## Diagnosing Results

Look for:

- bottlenecks: queue growth, high utilization, delayed replenishment, blocked flow
- nonlinear thresholds: small input change causing large output change
- feedback effects: reinforcing growth, balancing limits, oscillation, overshoot
- heterogeneity effects: outcomes concentrated in agent groups or network regions
- physical constraints: collisions, saturation, instability, energy or geometry limits
- stochastic fragility: a conclusion that changes across seeds or rare events

## Comparing Methods

When multiple methods could explain the same phenomenon, state the trade-off:

- ABM explains heterogeneous local behavior and emergence.
- DES explains timing, resources, queues, and process bottlenecks.
- System dynamics explains aggregate feedback and long-run policy structure.
- Physics simulation explains motion, control, collision, and continuous constraints.
- Monte Carlo explains uncertainty propagation when internal dynamics are simple.

## Next Experiment

Suggest a next experiment only when it would materially affect the decision. Good next experiments usually test:

- the most sensitive assumption
- the most plausible competing intervention
- the smallest model extension needed to represent a missing mechanism
- calibration against observed baseline data
