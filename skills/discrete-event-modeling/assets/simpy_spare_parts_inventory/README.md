# SimPy Spare Parts Inventory

Models stochastic spare-part demand with reorder-point replenishment and delivery lead time. Use it for stockout risk, repair readiness, logistics delay, and service-level experiments.

Key entities are part demands, on-hand stock, and replenishment orders. The primary mechanisms are random demand, reorder threshold policy, lead-time delay, stockouts, and service level.

The bundled experiment varies `reorder_point` and reports `service_level` as the primary metric.
