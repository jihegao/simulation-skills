# Result Interpretation Reference

ABM outputs are generated evidence from encoded rules. Interpret them as behavior of the model, not automatic truth about the outside world.

## Minimum Explanation

Include:

1. Experiment question.
2. Model scope and important assumptions.
3. Parameters varied and fixed.
4. Number of runs, seeds, and steps.
5. Primary metric summary with values from `summary.json`.
6. Run-to-run variation or stochastic uncertainty.
7. Practical interpretation and limits.

## Wording Pattern

Use claims like:

- "In this model, increasing X was associated with higher/lower Y."
- "Across N seeded runs, final Y averaged A with range B-C."
- "This suggests the rule set is sensitive to X under these assumptions."

Avoid claims like:

- "This proves X causes Y" unless the user supplied calibrated validation evidence.
- "The optimal policy is..." from a small exploratory sweep.

## Reading `summary.json`

Focus on:

- `run_count`, `steps`, and `seeds` for evidence scope.
- `metrics.<metric>.mean/min/max` for aggregate outcomes.
- `parameter_effects` for direction of parameter trends.
- `interpretation` for a generated first-pass summary that should be checked against raw values.

When trends are weak, say they are weak. When ranges overlap heavily, report uncertainty instead of forcing a clean story.

## Local Experience Capture

After explaining a completed model from CSV/JSON evidence, save a compact private record with `scripts/save_model_experience.py`. Store it under `.mesa-abm-experience/` and treat it as local private user data, not public evidence or a scenario catalog entry.
