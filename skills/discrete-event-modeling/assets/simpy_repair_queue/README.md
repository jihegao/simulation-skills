# SimPy Repair Queue

Models repair requests arriving to a limited repair crew. Use it for maintenance backlog, service desks, depot repair, inspection stations, and other resource-constrained queues.

Key entities are repair jobs and repairers. The primary mechanisms are stochastic arrivals, stochastic service durations, queue waiting, crew utilization, and throughput.

The bundled experiment varies repairer capacity and reports `average_wait` as the primary metric.
