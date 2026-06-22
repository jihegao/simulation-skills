# DES Scenario Packs

Use this directory for reusable discrete-event simulation scenario packs such as
queues, repair support, production lines, inspection systems, and spare-parts
inventory flows.

Each pack should describe the modeling pattern, entities, resources, arrivals,
service processes, decision variables, metrics, experiment protocol, and export
path to `modeling-ir/v0` or a SimAgent-compatible spec.

Keep SimAgent runtime fixtures in `simulator`; this directory is for modeling
expertise and reusable scenario structure.

The current runnable starter packs live under `../assets/`:

- `simpy_repair_queue`: maintenance and repair resource queue.
- `simpy_spare_parts_inventory`: stochastic demand and replenishment policy.
