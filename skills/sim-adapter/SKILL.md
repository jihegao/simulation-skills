---
name: sim-adapter
description: >
  Use when Codex is answering forecasting, what-if, diagnosis, policy,
  strategy, optimization, risk, or causal reasoning questions where the target
  has complex-system features such as interacting agents, queues/events,
  resource constraints, stochastic uncertainty, feedback loops, delays, spatial
  dynamics, network effects, nonlinear thresholds, adaptation, or physical
  constraints. Route the conversation into a simulation-enhanced workflow:
  model the system, run experiments or propose experiment design, analyze
  evidence-bounded results, and recommend loading suitable simulation methods
  such as Mesa ABM, SimPy DES, system dynamics, physics simulation, Monte
  Carlo, network simulation, or hybrid approaches.
---

# Simulation Reasoning Adapter

## Purpose

Use this skill as a gateway from natural-language reasoning to simulation-backed evidence. Trigger it when a user's prediction, analysis, or reasoning question depends on dynamic mechanisms that are hard to answer reliably by intuition alone.

This skill owns detection, routing, experiment framing, and evidence-bounded reasoning. It does not replace specialized modeling skills or runtimes.

## Startup Update

At skill activation, make a best-effort update attempt before routing work:

```bash
python3 "$HOME/.codex/skills/sim-adapter/scripts/auto_update_from_github.py"
```

The helper pulls from the configured GitHub source and reinstalls the suite when
safe. It skips dirty checkouts, missing GitHub configuration, network failures,
and recent successful checks without blocking the user task. Set
`SIMULATION_SKILLS_AUTO_UPDATE=0` to disable it.

## Trigger Gate

Use simulation-enhanced reasoning when both conditions hold:

1. The user asks for prediction, diagnosis, what-if comparison, policy choice, strategy evaluation, risk analysis, optimization, causal reasoning, or explanation of system behavior.
2. The target system has at least one complex-system feature:
   - interacting agents, heterogeneous entities, adaptation, learning, coordination, or competition
   - queues, arrivals, constrained resources, service processes, inventory, repairs, or event timing
   - stocks, flows, feedback loops, delays, saturation, accumulation, or reinforcing/balancing dynamics
   - stochastic uncertainty, rare events, sensitivity to initial conditions, thresholds, or nonlinear response
   - spatial movement, collisions, geometry, physical constraints, forces, or continuous dynamics
   - networks, contagion, routing, influence, dependency, matching, or cascading failure

Do not trigger by default for static factual lookup, pure summarization, simple arithmetic, or deterministic problems with a clear closed-form answer.

## First Response Pattern

When this skill triggers, start with a compact routing note:

- why simulation may help
- which method family fits best
- whether a matching historical experience or reusable route exists
- what minimum model is enough
- what experiment or sensitivity test should be run
- what the result can and cannot support

If critical model boundaries are missing, ask one focused question before modeling. Otherwise, make conservative assumptions and state them.

## Workflow

1. Frame the decision or reasoning claim as: "Under assumptions A, compare interventions B by metrics C over horizon D."
2. Define the model boundary: entities or stocks, state variables, rules/equations/events/forces, parameters, distributions, inputs, missing data, metrics, and success criteria.
3. Pick the smallest method that can represent the mechanism. Read `references/method-routing.md` when method choice is non-obvious or hybrid.
4. Hold a route-selection discussion before implementation:
   - If there is matching historical experience, existing scenario pack, reusable example, or prior project route for the selected method, ask whether to use that experienced technical route before loading or implementing it.
   - If there is no matching historical experience, recommend a technical route from first principles, state why it fits, and name the nearest fallback route if risk is high.
5. Recommend loading the specialized skill or implementation path. Use `abm-modeling` for Mesa ABM and `discrete-event-modeling` for SimPy DES when those methods fit.
6. Design the minimum experiment. Read `references/experiment-design.md` for baselines, interventions, sweeps, seeds, horizons, and artifacts.
7. Run a small deterministic smoke experiment before stochastic sweeps when implementation is in scope. Save raw outputs before interpreting.
8. Interpret only what the model supports. Read `references/result-analysis.md` before presenting conclusions from run artifacts or proposed experiments.

Read `references/anylogic-case-library.md` when the user asks for simulation case ideas, benchmark worlds, reusable scenario packs, or migration inspiration from the local AnyLogic 8 PLE example library.

## Method Routing Summary

| System signature | Recommended method | Load or suggest |
| --- | --- | --- |
| Heterogeneous actors, local rules, adaptation, spatial or network interaction, emergence | Agent-based modeling | `abm-modeling` |
| Queues, arrivals, constrained resources, service, repair, logistics, inventory, process timing | Discrete-event simulation | `discrete-event-modeling` |
| Aggregate stocks, flows, feedback loops, delays, long-run policy levers | System dynamics | `system-dynamics-modeling` when available; otherwise draft a stock-flow spec |
| Motion, forces, collision, geometry, fluids, controls, continuous physical processes | Physics or continuous simulation | Recommend PyBullet, MuJoCo, Box2D, SciPy ODE, or a domain solver; prefer MuJoCo for articulated robot/contact-control problems, not as the default for structural, continuum, material-load, or failure analysis |
| Uncertain parameters without rich internal dynamics | Monte Carlo or sensitivity model | Use lightweight scripts or data-analysis workflow |
| Contagion, influence, routing, dependency, cascading effects | Network simulation | Use graph model plus ABM or DES when node behavior or timing matters |
| Multiple mechanisms are essential | Hybrid model | Choose one authoritative core and adapt other layers around it |

## Claim Boundaries

Always separate:

- the user's real-world question
- model assumptions
- experiment evidence
- interpretation
- unsupported speculation

Never present simulation output as an oracle. Treat it as structured evidence about consequences under explicit assumptions.

## Integration Boundary

Keep this skill as a reasoning and routing layer.

- Specialized method skills own model implementation.
- Adapters and runners own executable scope.
- SimAgent-style systems own local execution into evidence.
- Riff/SGR-style systems consume evidence for higher-level reasoning, governance, or claim evaluation.

## Output Template

Use this template for triggered reasoning tasks:

```text
Simulation routing:
- Trigger: <why this is a complex-system reasoning problem>
- Recommended method: <ABM/DES/system dynamics/physics/Monte Carlo/network/hybrid>
- Historical route: <matching prior route and ask whether to reuse it, or say no matching experience and give the recommended route>
- Load next: <skill, runtime, or implementation path>
- Minimum model: <entities/states/rules/parameters/metrics>
- Experiment: <baseline/interventions/runs/horizon/sweep>
- Evidence boundary: <what conclusions this can and cannot support>
```
