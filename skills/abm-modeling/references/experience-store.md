# Local Experience Store

Use the local experience store after completing a new Mesa model and producing CSV/JSON evidence. The store is private user data by default and must stay out of Git unless the user explicitly asks to export or publish it.

Default location:

```text
.mesa-abm-experience/
  index.jsonl
  models/
  summaries/
```

## Save Command

```bash
python3 abm-modeling/scripts/save_model_experience.py \
  --model path/to/model.py \
  --config path/to/experiment.json \
  --summary path/to/output/summary.json \
  --output-root .mesa-abm-experience \
  --notes "Short lessons learned"
```

## What To Save

Save compact modeling experience: assumptions, parameters, primary metrics, reusable implementation choices, pitfalls, and next-step guidance. The card should point to raw evidence paths instead of copying per-run CSV data.

## Privacy Rules

- Treat `.mesa-abm-experience/` as local private user data.
- Do not commit generated experience cards by default.
- Do not publish local notes unless the user explicitly asks.
- Keep result claims bounded by the saved Mesa evidence.
