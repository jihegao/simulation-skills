# ABM Source Parsing

Use this reference when the source is an existing ABM project from NetLogo,
Repast/Repast Simphony, Mesa, or a mixed ABM codebase. The goal is structural
extraction for conversion, not runtime-equivalent import.

## Quick Inspection

Run the bundled inspector first when files are available:

```bash
python skills/simulation-model-conversion/scripts/inspect_abm_source.py <source> --format markdown
```

Use `--source-type netlogo`, `--source-type repast`, or `--source-type mesa`
when auto-detection is ambiguous. Save or paste the JSON output when a mapping
table or follow-up implementation needs exact names.

Treat the report as evidence for:

- Agent classes, breeds, context objects, and state variables.
- Spatial projections such as grids, patches, networks, geography, and
  continuous spaces.
- Scheduler entry points such as `go`, `step`, `@ScheduledMethod`, or Mesa
  `step` methods.
- Parameters, widget defaults, experiment controls, and data collectors.
- Metrics, plots, monitors, and visualization requirements.

## NetLogo

Inspect `.nlogo` files for:

- `breed`, `directed-link-breed`, and `undirected-link-breed`.
- `globals`, `turtles-own`, `patches-own`, and `links-own`.
- `to setup`, `to go`, reporters, link creation, patch access, and plot calls.
- Interface widgets: sliders, switches, choosers, buttons, monitors, and plots.
- BehaviorSpace experiments when present in later `.nlogo` sections.

Conversion notes:

- Map breeds to agent classes and `*-own` blocks to state fields.
- Map `patches` and coordinate primitives to a grid or cell layer.
- Preserve NetLogo tick semantics explicitly; do not assume Mesa scheduler order
  matches `ask` ordering.
- Record widget defaults and BehaviorSpace ranges as experiment parameters.

## Repast / Repast Simphony

Inspect Java source plus `parameters.xml`, `.rs`, `.score`, Maven, or Gradle
files for:

- `ContextBuilder` implementations and context population logic.
- Agent classes, projections, `Grid`, `ContinuousSpace`, `Geography`, and
  `Network` builders.
- `@ScheduledMethod` annotations, priorities, start times, and intervals.
- `RunEnvironment.getInstance().getParameters()` calls.
- Watchers, data sets, charts, batch parameters, and scenario artifacts.

Conversion notes:

- Preserve scheduled method priority and interval before translating to Mesa or
  SimPy loops.
- Treat projection builders as first-class mapping items; they often define
  movement and neighbor semantics.
- Keep Java package/class names in the mapping table so behavior can be traced
  back to source files.

## Mesa

Inspect Python files with AST plus manual review for:

- `mesa.Model` and `mesa.Agent` subclasses.
- Model constructor parameters and random seed handling.
- `step`, `advance`, staged activation, agent sets, and scheduler use.
- Grid, continuous space, network, and data collector objects.
- Solara or browser visualization modules and chart/reporting code.

Conversion notes:

- Mesa 3 often uses model-owned agent sets instead of older scheduler classes;
  inspect `model.agents`, `agents_by_type`, and explicit iteration order.
- Keep `DataCollector` reporters as candidate output metrics.
- For static/browser targets, separate model state transitions from Solara
  callbacks before porting UI behavior.

## Mixed Or Unsupported Sources

If the inspector cannot parse the model, still build a manual mechanism
contract from source files. Search for agent nouns, state variables, schedule
entry points, random draws, neighbor queries, parameter readers, and output
writers. Mark every unsupported or dynamic feature as an approximation in the
mapping table.
