# Conversion Checklist

## Source Inspection

- Source path and format.
- Original model time unit and horizon.
- Components, agents, resources, queues, stocks, or networks.
- Statecharts, events, transitions, service processes, or equations.
- Parameters, distributions, default values, and controls.
- Metrics, costs, logs, plots, and visual animation requirements.
- For ABM source projects, include the output from
  `scripts/inspect_abm_source.py` when the source is NetLogo, Repast, or Mesa.

## Mapping Table

Use a compact table:

| Source element | Target element | Mapping type | Notes |
| --- | --- | --- | --- |
| Component or agent | Class/object | direct/approximation | State variables |
| State | String/enum/state field | direct/merged/split | Entry/exit actions |
| Transition/event | Method/process/timer | direct/approximation | Trigger and timing |
| Queue/resource | list/Resource/Store | direct/approximation | Priority rules |
| Metric | snapshot field/chart | direct/derived | Units and denominator |

## Implementation Checks

- Seeded randomness produces reproducible smoke runs.
- The first test fails before implementation and passes after.
- State transitions cover at least one normal and one edge path.
- Output files are deterministic enough for tests.
- Browser views have stable `data-layer`, `data-chart`, or `data-panel` markers.
- Continuous animation has Start/Stop and does not require page reload.

## Common Conversion Choices

- AnyLogic agent/statechart model to Mesa: keep agents as Python objects and
  statechart states as explicit string fields or enums.
- NetLogo to Mesa: map breeds to agent classes, `*-own` blocks to state fields,
  patches to a grid layer, and `setup`/`go` tick semantics to explicit model
  methods.
- Repast to Mesa: map `ContextBuilder` population to model initialization,
  projections to Mesa spaces or networks, and `@ScheduledMethod` annotations to
  explicit step phases with preserved priority/interval notes.
- Mesa to another target: extract model/agent classes, constructor parameters,
  scheduler or agent-set iteration order, spaces, and `DataCollector` reporters.
- AnyLogic process blocks to SimPy: map seize-delay-release to `Resource`
  requests and `env.timeout`.
- Mesa/Solara to legacy JS: move model state and step rules into browser-side
  objects, render SVG/HTML directly, and replace server callbacks with DOM
  events and `setInterval`.
- Python model to static replay: generate frames in Python and keep browser JS
  limited to playback and charts.

## Final Review

- Does the target preserve the decision mechanism?
- Are unsupported runtime-equivalence claims removed?
- Can the user run the model and see outputs with documented commands?
- Are generated artifacts ignored or intentionally tracked?
