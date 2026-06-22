# AnyLogic Case Library Notes

Use these notes as a source of case requirements and transferable modeling ideas from the local AnyLogic 8 PLE example library. Do not copy `.alp` files, images, or generated code into downstream projects by default; treat the source models as examples to paraphrase, inspect, and adapt.

Local source inspected: `/Users/Shared/AnyLogic 8 PLE/eclipse/plugins/com.anylogic.examples_8.9.0.202404161223/`

Primary evidence:

- `registry.xml`: model titles, descriptions, tags, and product requirements.
- `.alp` XML files: structural evidence for agents, variables, functions, embedded objects, statecharts, experiments, and model time unit.
- `alp-importer`: optional structural importer at `/Users/gaojihe/apps/sgr-stack/skills/alpImporter`.

## Coverage

The registry contains:

- 113 full example models under `models/`
- 142 how-to/basic models under `basicmodels/`
- 50 system dynamics examples under `sdmodels/`
- Big Book examples grouped by topics such as three methods, multimethod, statecharts, field service, data exchange, events, controls, agents, and output data

The main tagged example families are agent-based, system dynamics, discrete event, pedestrian, fluid, GIS/database, material handling, road traffic, and rail.

## Use Pattern

When a user needs a new simulation scenario, translate an AnyLogic case into:

1. Decision question: what policy, capacity, rule, or design is being compared.
2. System boundary: agents, resources, stocks, flows, networks, places, and events.
3. Dynamics: state transitions, queues, service/resource seizure, movement, failures, feedback loops, or routing.
4. Metrics: throughput, waiting time, utilization, cost, risk, unmet demand, delivery time, service level, or outcome counts.
5. Experiment: baseline, intervention knobs, sweep parameters, seeds, horizon, and calibration data.
6. Migration route: Mesa ABM, SimPy DES, system dynamics equations, graph/network simulation, fluid/material-flow approximation, or hybrid model.

## Representative Case Cards

### Airline Fleet

- Requirement: manage aircraft engineering lifecycle, scheduled maintenance, repairs, spares purchasing, replacement after failure, and unexpected breakdowns. Compare monthly spare order policies and emergency purchases by inventory cost and unexpected expense.
- Model idea: aircraft and spare parts are stateful agents with age, remaining life, maintenance/repair status, and procurement lead time. Add an optimization experiment over order quantity and emergency purchase thresholds.
- Migration route: ABM for aircraft/spares lifecycle plus DES queues for maintenance bays and repair crews.

### Aircraft Fleet Planning

- Requirement: maintain 20 aircraft under weekly and flight-hour based checks. Minimize deferred maintenance backlog while meeting flight plan targets.
- Model idea: aircraft agents accumulate flying hours and weekly obligations; maintenance decisions allocate aircraft into checks. Backlog carries into the next week when targets are missed.
- Migration route: ABM for aircraft state plus scheduling/optimization layer for maintenance allocation.

### Field Service

- Requirement: choose repair crew count and replacement policy for geographically distributed revenue-generating equipment. Failures create repair requests with deadlines; late or aging repairs can fail and force replacement.
- Model idea: equipment agents have working/failed/repaired/replaced states; crews are mobile resources assigned to service requests; cost and revenue accumulate by equipment status and crew operations.
- ALP structural sample: 3 components (`Main`, `EquipmentUnit`, `ServiceCrew`), 24 variables, 8 functions, 9 states, 21 transitions, model time unit `Day`.
- Migration route: Mesa ABM on GIS or abstract coordinates; add DES event queue for request arrivals, crew dispatch, travel, and repair completion.

### Maintenance Phase 7

- Requirement: model maintenance service with multiple transport modes and service requests over an hourly horizon.
- Model idea: assets generate service requests; maintenance center dispatches truck/helicopter/transport resources; turbine and request statecharts represent degradation, request, travel, service, and completion.
- ALP structural sample: 7 components, 8 variables, 3 functions, 8 states, 10 transitions, model time unit `Hour`.
- Migration route: DES for requests/resources plus ABM if spatial dispatch and transport choice matter.

### Border Checkpoint

- Requirement: evaluate international checkpoint flow with separate car and bus processes. Cars pass lanes, document booths, vehicle inspection, and possible full inspection; bus passengers disembark, queue for document checks, then reboard after bus inspection.
- Model idea: combine vehicle agents, pedestrian/tourist agents, lane resources, inspection modules, bus process synchronization, and traffic-light style queue control.
- ALP structural sample: 9 components, 51 variables, 12 functions, 72 embedded objects, 1 experiment, model time unit `Minute`.
- Migration route: hybrid DES plus pedestrian/traffic abstraction. SimPy can reproduce queues and resources; Mesa can represent people/vehicles and spatial movement if needed.

### Consumer Credit

- Requirement: compare staffing for consumer-loan application handling across office, web, and internet-bank channels. Applications pass scoring, personal review, and credit-rating inspection.
- Model idea: application entities flow through staged verification blocks; staff pools are constrained resources; approvals/rejections are recorded by stage and channel.
- Migration route: SimPy DES with resource pools and routing probabilities; optimize staff count against turnaround time and utilization.

### Emergency Department

- Requirement: explore patient length of stay and resource utilization in an emergency department with registration, triage, X-ray, ultrasound, and multiple resource types.
- Model idea: patient entities traverse a care network; nurses, assistants, experts, rooms, and portable devices are resources; live parameter changes show resource bottlenecks.
- Migration route: SimPy DES; optional network layout or Mesa visualization for patient movement.

### Job Shop

- Requirement: assess production plans for a factory where raw materials wait before CNC machining, finished products wait before shipment, and users vary processing time and labor.
- Model idea: orders/entities flow through receiving, storage, machining, finished storage, and shipping; labor and machines are constrained resources; costs and utilization are tracked.
- Migration route: SimPy DES with machine/labor resource pools and scenario sweeps over staffing and processing-time assumptions.

### Crude Oil Pipeline Network

- Requirement: evaluate a database-parameterized oil pipeline network with terminals, tanks, pipelines, commodity batches, route rules, pipeline failures, MTTF/MTTR, throughput, utilization, and delivery time.
- Model idea: batches carry commodity and destination route; tanks enforce compatible commodity storage; pipelines are seizeable flow resources with failure/repair downtime; dispatch places batches into compatible or empty tanks, then releases by FIFO.
- ALP structural sample: 8 components (`OilPipeline`, `OilTerminal`, `OilTank`, `OilBatch`, endpoints, and `Main`), 42 variables, 35 functions, 25 embedded objects, model time unit `Day`.
- Migration route: DES or hybrid flow-network simulation. Preserve tables for terminals, tanks, pipelines, commodity routes, failure rates, and repair times.

### Grain Terminal

- Requirement: model grain unloading from trucks and trains into silos, then loading from main silos into ships. Truck unloading waits for suitable silo lines; auto silos trigger transfer at 90% capacity; ship holds can each contain only one grain type.
- Model idea: batches of grain move through auto silos, main silos, transport lines, berths, and ship holds; resource constraints include lines, silos, train/ship berths, and product compatibility.
- Migration route: DES/material-flow approximation with compatibility constraints and berth/resource utilization metrics.

### Warehouse Conveyor

- Requirement: represent conveyor-based warehouse item movement and bottlenecks.
- Model idea: items travel through conveyor segments and transfer points; segment speed, capacity, merges, splits, and buffers determine throughput and blocking.
- Migration route: SimPy DES with conveyor segments as capacity/time-delay resources; add graph routing if there are multiple paths.

### Traffic Light Phases Optimization

- Requirement: choose durations for three signalized intersections to minimize vehicle time in system.
- Model idea: vehicles arrive from road-network entries; traffic-light phase durations are control variables; queue lengths and travel times define the objective.
- Migration route: traffic DES or cellular/agent road model. Run sweeps over phase lengths with common demand scenarios.

### SIR Agent Based Networks

- Requirement: compare disease spread dynamics across distance-based, random, unrestricted, small-world, and ring-lattice social networks.
- Model idea: `Person` agents hold S/I/R states; infection occurs probabilistically through network contacts; experiments include simple simulation and Monte Carlo.
- ALP structural sample: 2 components (`Main`, `Person`), 12 variables, 1 function, 3 states, 5 transitions, 2 experiments, model time unit `Day`.
- Migration route: Mesa ABM with NetworkX topology generation and replicated stochastic runs.

### Schelling Segregation

- Requirement: show how mild local preference can produce macro segregation.
- Model idea: two agent groups occupy grid cells; each agent evaluates neighbor similarity; unhappy agents move to empty cells; a satisfaction threshold controls segregation strength.
- Migration route: Mesa grid ABM with sweep over satisfaction threshold, density, neighborhood radius, and seed.

### Bass Diffusion Agent Based

- Requirement: model product adoption from advertising and peer influence across a large population.
- Model idea: people are potential/adopted agents; advertising causes exogenous adoption and peer links cause endogenous contagion. The original example assumes a fully connected network for a large population.
- Migration route: Mesa ABM or aggregate Bass system dynamics; choose ABM when heterogeneity or network structure matters.

### Supply Chain

- Requirement: optimize inventory policies for retailer, wholesaler, and factory under customer demand. Compare ordering/production/holding/stockout costs and customer wait time.
- Model idea: supply-chain nodes observe inventory daily, place orders, produce against policy, and accumulate costs; customer demand creates backlog when stock is insufficient.
- Migration route: hybrid DES/system dynamics; use stock-flow equations for aggregate inventory or DES for order-level queues and lead times.

### Air Defense System

- Requirement: protect coastal assets from bomber attacks with radars that have limited coverage and missile scanning capacity. Users vary aircraft speed and radar performance.
- Model idea: aircraft agents receive target assets; radar agents detect/track within range and capacity; aircraft use continuous movement behavior.
- Migration route: Mesa ABM or continuous agent simulation with spatial geometry, detection constraints, and defense success/risk metrics.

## Structural Inspection Recipe

Use `alp-importer` only when raw `.alp` structure is needed:

```bash
file "/Users/Shared/AnyLogic 8 PLE/eclipse/plugins/com.anylogic.examples_8.9.0.202404161223/models/Field Service/Field Service.alp"
python3 /Users/gaojihe/apps/sgr-stack/skills/alpImporter/scripts/import_anylogic_alp.py \
  --alp "/Users/Shared/AnyLogic 8 PLE/eclipse/plugins/com.anylogic.examples_8.9.0.202404161223/models/Field Service/Field Service.alp" \
  --output-dir /tmp/alp-field-service
```

Read `anylogic_model_ir.json` or `import_report.md` before making claims about an `.alp` model. The importer preserves structural evidence but does not prove behavioral equivalence with AnyLogic.

## Claim Boundaries

- These notes are paraphrased model requirements and transferable design ideas derived from the local library.
- Do not treat case cards as executable specifications; check `registry.xml` and the selected `.alp` before implementation.
- AnyLogic library-specific elements such as Road Traffic, Pedestrian, Rail, Fluid, and Material Handling blocks may need approximation in Python runtimes.
- Use the smallest model that preserves the decision mechanism; avoid cloning every AnyLogic animation or UI detail.
