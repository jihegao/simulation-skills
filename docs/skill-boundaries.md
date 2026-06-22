# Skill Boundaries

## Repository Shape

This repository is a skill suite. GitHub uses a nested source layout:

```text
skills/<skill-name>/
```

Codex installation uses a flat runtime layout:

```text
~/.codex/skills/<skill-name>/
```

Do not make a full method skill a nested child of another skill.

## Ownership

- `sim-adapter` owns detection, method routing, experiment framing, and
  evidence-boundary language.
- `abm-modeling` owns Mesa ABM implementation workflows, experiment runners,
  visualization generation, scenario packs, and ABM result interpretation.
- `discrete-event-modeling` owns SimPy DES implementation workflows, queue and
  resource models, DES scenario assets, and DES result interpretation.
- `simulation-model-conversion` owns conversion workflows from model
  descriptions, AnyLogic/Mesa/SimPy structures, or visual prototypes into
  runnable artifacts.
- `examples/` owns runnable sample models and copied reproduction artifacts.

## Routing Rule

Use `sim-adapter` first when the user is asking a forecasting, what-if,
diagnosis, policy, optimization, risk, or causal reasoning question with
complex-system behavior. Once the method is clear, load the appropriate sibling
skill for implementation or detailed analysis.

## Publication Rule

The public repository should not include virtual environments, generated
outputs, Python caches, local `.git` directories copied from source repos, or
private runtime files. Keep generated evidence under ignored `outputs/` unless
an example artifact is intentionally promoted into tracked documentation.
