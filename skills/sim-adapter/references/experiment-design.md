# Experiment Design

Design the smallest experiment that can change the user's conclusion.

## Minimum Experiment

Define:

- question: the decision or claim being tested
- baseline: current or reference scenario
- interventions: one or more changed policies, designs, thresholds, or parameters
- metrics: primary outcome, secondary outcomes, and guardrails
- horizon: simulated time span and warm-up period if needed
- repetitions: seeds or runs when randomness matters
- sweep: parameter ranges that test sensitivity
- artifacts: raw rows, summary JSON/CSV, plots when useful, and a short analysis note

## Smoke Run

Before a full sweep, run or request a small deterministic smoke experiment:

- one baseline
- one intervention or one changed parameter
- short horizon
- fixed seed
- sanity checks on metric direction and units

Use the smoke run to catch model wiring errors, not to make a final claim.

## Stochastic Runs

When randomness matters:

- use multiple seeds
- report mean and variation
- preserve run-level rows
- compare interventions using the same seed set when possible
- flag wide uncertainty instead of hiding it behind a single average

## Sensitivity

Run sensitivity tests for assumptions that are uncertain and decision-relevant:

- arrival rate, demand, service time, failure rate, adoption rate, lead time, compliance, resource capacity
- behavioral rules, thresholds, network density, physical coefficients, controller parameters

Prefer a small interpretable sweep over a large opaque one.

## Calibration And Validation

State what data would calibrate or validate the model:

- historical outcomes for baseline fit
- observed process times, queues, utilization, flows, failure rates, or movement patterns
- expert constraints for impossible or implausible states

If no calibration data exists, call the result exploratory scenario evidence.

## Output Artifacts

Prefer durable artifacts:

- `summary.json` for experiment setup, parameters, metrics, and aggregate results
- `summary.csv` or equivalent for tabular comparisons
- run-level CSV rows when stochastic variation matters
- model spec or config file when the model may be rerun

Do not rely on screenshots or visual inspection as the only evidence.
