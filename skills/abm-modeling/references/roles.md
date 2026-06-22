# Role-Based Workflow

Use this reference when a Mesa ABM task needs more structure than a single
linear edit. This is a role-based workflow, optionally subagent-dispatchable. It
does not require real subagents: one agent can run the roles sequentially
as checklists. If subagent tools are available and the task is large, dispatch
bounded side work and keep the main agent responsible for integration.

## Role Order

1. Governor
2. Model Designer
3. Simulator
4. Verifier
5. Result Analyst

## Roles

### Governor

Own scope, boundaries, and evidence standards.

- Restate the experiment question and success criteria.
- Keep the work inside the Mesa-only scope for this stage.
- Define what evidence is required before claims are allowed.
- Block unsupported claims, behavioral-equivalence claims, and visualization-only
  conclusions.
- Decide whether optional subagents are useful for independent side work.

### Model Designer

Turn the phenomenon into a runnable model design.

- Define agents, environment, state variables, actions, scheduling, parameters,
  stochastic sources, and metrics.
- Keep the first design minimal enough to run.
- Name the smoke experiment and any stochastic sweep before implementation.
- Identify assumptions and known omissions.

### Simulator

Implement or adapt the Mesa model and run experiments.

- Prefer existing scripts such as `scripts/run_mesa_experiment.py`.
- Produce raw CSV/JSON evidence, not just screenshots or browser output.
- Keep seeds, steps, parameter grids, and output paths explicit.
- Generate SolaraViz only after a batch run succeeds.

### Verifier

Check that the implementation and evidence support the claim.

- Run the relevant unit tests and quick validation commands.
- Inspect output schema, run counts, metric names, and reproducibility inputs.
- Confirm generated visualization modules import under the Mesa runtime when
  visualization was produced.
- Mark any claim as unverified when evidence is missing or runtime support is
  unavailable.

### Result Analyst

Explain only what the evidence supports.

- Report experiment question, varied parameters, seeds/runs/steps, and primary
  metrics.
- Separate observed trends from causal claims.
- State stochastic variation, model assumptions, and limitations.
- Propose the smallest next experiment when current evidence is inconclusive.

## Optional Subagent Dispatch

Use real subagents only for bounded, independent work:

- Model Designer can draft a design from requirements.
- Verifier can inspect tests, generated outputs, or docs for claim drift.
- Result Analyst can independently summarize `summary.json` and CSV outputs.

Do not delegate final integration, scope control, or evidence claims away from
the main agent. The Governor role stays with the main agent unless the user
explicitly asks for a separate governance review.

## Handoff Template

```text
Role: <Governor | Model Designer | Simulator | Verifier | Result Analyst>
Task: <bounded task>
Inputs: <files, configs, outputs>
Do not modify: <paths or constraints>
Return: <specific artifact or checklist result>
Evidence required: <tests, output files, or exact observations>
```
