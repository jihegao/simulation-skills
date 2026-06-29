# Method Routing

Use the smallest method that can represent the mechanism the user cares about. Prefer a clear, limited model over an impressive mixed stack.

## Route Selection Discussion

After selecting the modeling paradigm, check whether there is a same-family historical route before moving into implementation:

- Treat experience as matching only when the prior route shares the dominant mechanism, data shape, implementation stack, and validation style. A similar domain label is not enough.
- If a matching route exists, ask whether to use the experienced route and name the concrete asset or pattern to reuse, such as a scenario pack, example model, runner, visualization path, or experiment harness.
- If no matching route exists, give a recommended technical route immediately. Include the chosen library or stack, the first smoke model to build, the minimum evidence artifact, and the nearest fallback if the recommendation proves too heavy.
- If experience is partial, call it a near match and recommend which parts to reuse and which parts to redesign.

Keep the discussion short: one route decision, one reason, one next action.

## Agent-Based Modeling

Choose ABM when macro behavior depends on local decisions or interaction among heterogeneous entities.

Good fit:

- people, vehicles, firms, teams, animals, or devices with individual state
- adaptation, learning, imitation, competition, coordination, or local rules
- spatial neighborhoods, networks, contagion, clustering, segregation, or emergence
- policy effects that differ by agent type

Recommend loading `abm-modeling` for Mesa-based implementation, sweeps, visualization, and evidence-bounded ABM interpretation.

## Discrete-Event Simulation

Choose DES when system performance depends on event timing, queues, resources, or process flow.

Good fit:

- arrivals, service, queues, reneging, priorities, batching, scheduling, repair, downtime
- constrained crews, machines, docks, beds, servers, inspectors, or inventory
- throughput, utilization, wait time, delay, stockout, service level, turnaround time

Recommend loading `discrete-event-modeling` for SimPy-based implementation and experiment evidence.

## System Dynamics

Choose system dynamics when the right unit is an aggregate stock or flow rather than individual entities.

Good fit:

- population, capacity, backlog, cash, inventory, trust, adoption, pollution, capability
- feedback loops, delays, saturation, long-run policy levers, compounding, overshoot
- decisions where structure matters more than per-entity heterogeneity

If no installed system-dynamics skill exists, draft a stock-flow spec with stocks, flows, auxiliaries, feedback loops, equations, units, parameters, and calibration needs.

## Physics Or Continuous Simulation

Choose physics or continuous simulation when geometry, motion, forces, collision, control, or differential equations are the core mechanism.

Good fit:

- robotics, vehicles, trajectories, collision avoidance, rigid bodies, fluids, thermal systems, mechanical systems
- controllers, stability, response curves, safety envelopes

Recommend an engine based on fidelity:

- SciPy ODE for small deterministic continuous systems
- PyBullet, MuJoCo, or Box2D for rigid-body interaction
- domain solvers for fluid, structural, thermal, or electrical systems

MuJoCo routing boundary:

- Recommend MuJoCo when the dominant mechanism is articulated rigid-body
  dynamics, joint constraints, robot balance/gait, contact-rich control,
  biomechanics, trajectory optimization, system identification, or
  reinforcement-learning environments.
- Do not make MuJoCo the default for structural, continuum, material-load, or
  failure-analysis questions such as stress/strain, buckling, glue or joint
  failure, deflection, fracture, fatigue, load rating, deformation fields, or
  stiffness/compliance. Route those to a structural/FEM solver, material model,
  multibody-flexible-body route, or simplified truss/beam/shell model first,
  depending on required fidelity.
- For browser-visible teaching prototypes, use Three.js plus a lightweight
  physics engine such as cannon-es, Rapier, or Ammo.js when interactivity and
  inspection matter more than engineering-grade structural fidelity.
- When a problem mixes articulated bodies or moving payloads with load-bearing
  structures, choose the authoritative layer explicitly: MuJoCo may own the
  moving rigid-body/contact controller, while structural response, material
  capacity, deformation, and failure should still be checked by a structural,
  continuum, or FEM-oriented route.

## Monte Carlo And Sensitivity Models

Choose Monte Carlo when uncertainty over parameters matters more than internal dynamics.

Good fit:

- forecasts with uncertain demand, cost, lead time, conversion rate, reliability, or risk
- decision comparisons where formulas are simple but inputs are uncertain

Use sampled assumptions, scenario tables, and sensitivity ranking. Do not label it a complex system model unless interactions or dynamics are explicitly represented.

## Network Simulation

Choose network simulation when topology drives outcomes.

Good fit:

- contagion, influence, routing, dependencies, cascades, diffusion, matching, supply networks

Use graph metrics and propagation rules. Combine with ABM when nodes behave adaptively, or DES when timing and queues matter.

## Hybrid Models

Use hybrid models only when one method cannot represent the decision mechanism.

Pick one authoritative core:

- DES core plus Mesa/SolaraViz visualization for queue/resource systems
- ABM agents plus DES service processes for people moving through constrained facilities
- system dynamics macro loop plus ABM micro behavior for adoption or capacity planning
- physics environment plus agent controllers for robotics, traffic, or collision-heavy systems

State which layer owns time, state, and metrics. Avoid making two engines independently authoritative for the same mechanism.
