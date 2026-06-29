# Simulation Case Library

This directory is the runnable case library for the Simulation Skills suite.
Each case should name its method family, runnable entrypoint, visualization
surface, and evidence boundary.

## Cases

| Case | Method | Entrypoint | Visualization | Evidence boundary |
| --- | --- | --- | --- | --- |
| `global_warming_system_dynamics` | System dynamics | `python3 -m examples.global_warming_system_dynamics.app --output examples/global_warming_system_dynamics/index.html` | `examples/global_warming_system_dynamics/index.html` | Short- and medium-term scenario checks for global CO2 stock, forcing, and temperature response; not a CMIP/IPCC-class Earth system model. |
| `air_defense_mesa` | Agent-based modeling | `python3 examples/air_defense_mesa/run_experiment.py` | `solara run examples/air_defense_mesa/app.py` | Local radar/missile engagement dynamics, not a validated defense simulation. |
| `field_service_mesa` | Agent-based modeling | `python3 examples/field_service_mesa/run_experiment.py` | `python3 examples/field_service_mesa/static_viewer.py` | Field-service dispatch mechanism reproduction, not an operational planning system. |
| `hospital_material_mesa` | Agent-based modeling | `python3 examples/hospital_material_mesa/run_experiment.py` | `solara run examples/hospital_material_mesa/app.py` | Hospital material-flow reproduction from parsed example geometry, not a hospital operations benchmark. |
| `des_mesa_queue` | Hybrid DES/ABM | `python3 -m examples.des_mesa_queue.run_experiment` | `solara run examples/des_mesa_queue/app.py` | Queueing demonstration with Mesa shell and SimPy timing. |
| `global_shipping_mesa` | Hybrid DES/ABM + GIS | `python3 -m examples.global_shipping_mesa.run_experiment` | `python3 -m examples.global_shipping_mesa.static_viewer` | Global port dispatch and congestion demo with embedded GIS points; not a calibrated maritime forecast. |
| `microgravity` | Physics-style structural check | `python3 examples/microgravity/run_experiment.py` | `python3 examples/microgravity/static_viewer.py` | Simplified structural envelope, not a finite-element solver. |
| `bdi_polarization_mesa` | BDI ABM + recommender dynamics | `python3 -m examples.bdi_polarization_mesa.run_experiment` | `python3 -m examples.bdi_polarization_mesa.single_run_viewer` | Exploratory reproduction of polarization-like dynamics from encoded BDI/recommendation/group-action rules; not calibrated platform evidence. |
