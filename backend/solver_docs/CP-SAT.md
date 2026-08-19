# CP-SAT Solver Workflow Explanation — ONE_V3 CubeSat Configurator

## 1. Big picture

The project currently contains three related solver paths:

1. **Main mission solver** used by the current configurator result / Solver Trace flow.
2. **Advanced subsystem optimization solver** exposed through the optimization API.
3. **Standalone CubeSat family solver / diagnostic solver** exposed through the `/api/solve/cubesat` route.

All three are based on the same general idea:

> Convert mission and payload requirements into engineering constraints, create a set of possible choices, then let Google OR-Tools CP-SAT select a feasible configuration.

In simple language, the solver behaves like an engineering shopping assistant. It has a list of possible buses, EPS units, ADCS units, computers, communication systems, thermal systems, and sometimes propulsion/radiation options. It rejects combinations that violate engineering limits. From the remaining valid combinations, it chooses the best one according to the objective function.

---

## 2. Main mission solver: `/api/v1/mission/solve`

This is the solver path currently used by the main configurator flow and Solver Trace page.

### Step 1 — User input

The user selects:

- Mission family, such as Remote Sensing, IoT / Communication, or Navigation
- Payload
- Region of interest
- Revisit time
- Optional engineering preferences

The backend receives this as a mission solve request.

### Step 2 — Payload resolution

If the user selected a catalog payload, the backend resolves the payload ID.

The resolver first checks the small seeded catalog. If the payload is not there, it searches the full master payload databases for Remote Sensing, IoT / Communication, and Navigation.

The payload is converted into a common engineering shape:

- Payload mass
- Payload dimensions
- Payload average power
- Payload peak power
- Nominal data rate
- Pointing requirement
- Thermal class

This is important because the solver does not directly reason about product names. It reasons about engineering numbers.

### Step 3 — Requirement derivation

The backend derives the solver requirements from the selected payload.

For the main mission solver, the key derived values are:

- Payload mass
- Payload volume
- Payload average power
- Payload peak power
- Minimum downlink rate
- Maximum allowed pointing error
- Thermal class

Example:

If a payload needs 18 Mbps downlink and 0.22 degree pointing, the solver must select a communication system that can support at least 18 Mbps and an ADCS option whose pointing error is no worse than 0.22 degrees.

### Step 4 — Constellation estimate

The backend estimates a simple constellation using the mission family, ROI type, and revisit time.

For example:

- Remote Sensing uses a Sun-synchronous orbit assumption
- IoT / Communication uses a LEO assumption
- Navigation uses an approximate MEO assumption

This estimate is currently mostly explanatory in the main mission solver. It is included in the report and trace, but the simple main solver does not yet scale every subsystem by constellation size.

### Step 5 — CP-SAT subsystem selection

The main solver creates a CP-SAT model.

It must choose exactly one item from each of these domains:

- Platform / bus
- EPS
- ADCS
- OBC
- Communication subsystem
- Thermal subsystem

The solver creates one Boolean variable for each candidate. For example:

- Choose 3U platform: yes/no
- Choose 6U platform: yes/no
- Choose EPS Basic: yes/no
- Choose EPS Plus: yes/no
- Choose ADCS Standard: yes/no
- Choose ADCS Precise: yes/no

Then it adds rules saying exactly one option must be chosen per domain.

### Step 6 — Engineering constraints

The main solver checks these constraints:

| Constraint | Meaning |
|---|---|
| Total mass <= bus mass capacity | The bus must be able to carry the payload and selected subsystems. |
| Total average power <= bus average power generation | The satellite must generate enough average power. |
| Total peak power <= bus peak power generation | The system must survive peak power loads. |
| Payload volume <= bus payload volume capacity | The payload must physically fit. |
| Communication downlink >= payload data need | The communication subsystem must support the data rate. |
| ADCS pointing error <= payload pointing requirement | The attitude control system must be accurate enough. |
| Enhanced thermal if payload is sensitive | Sensitive payloads require enhanced thermal support. |

Any architecture that violates one of these constraints is rejected.

### Step 7 — Objective function

The main mission solver uses a simple objective:

> Minimize total platform + subsystem cost.

That means the selected architecture is not necessarily the most powerful one. It is the cheapest one that still satisfies all constraints.

This is why the solver often selects basic components unless a requirement forces an upgrade.

### Step 8 — Engineering trace

After solving, the backend builds an engineering trace.

The trace explains:

- Which solver route was used
- What platform was selected
- Which subsystem components were selected
- What budgets and margins were calculated
- Whether constraints passed
- Why key subsystems were selected

---

## 3. Advanced subsystem optimization solver: `/api/v1/optimization/subsystems/solve`

This path is more detailed than the main mission solver.

It uses:

- Derived subsystem requirements
- Optional user constraints
- A richer CP-SAT subsystem selector

It chooses exactly one from these required domains:

- Structure
- EPS
- ADCS
- OBC
- Communication
- Thermal
- Propulsion

It can also select optional radiation support components.

### Additional constraints in the advanced solver

The advanced solver checks more things than the main mission solver, including:

- Storage requirement for OBC
- Battery energy requirement for EPS
- Downlink class
- Pointing accuracy
- Thermal mode
- Bus volume
- Bus power generation
- Peak power
- Cost cap if provided
- Propulsion recommendation
- Optional radiation risk support

### Advanced objective function

The advanced solver uses a weighted objective:

- Minimize cost
- Minimize mass
- Minimize risk
- Penalize mass over-budget
- Reward mass and power margin

So the advanced solver does not only choose the cheapest architecture. It tries to balance cost, mass, risk, and engineering margin.

In simple language:

> The main mission solver asks: “What is the cheapest design that works?”  
> The advanced optimization solver asks: “What design works well while balancing cost, mass, risk, and safety margin?”

---

## 4. Standalone CubeSat family solver and diagnostic solver

There is also a separate solver under `backend/solver`.

This solver is more tier-based. Instead of selecting individual named subsystem products from `catalog.json`, it selects architecture tiers such as:

- Bus class
- EPS tier
- ADCS tier
- Communication tier
- OBC tier
- Thermal tier
- Propulsion tier

### Normal CubeSat solve

The flow is:

1. Load all data
2. Load precomputed payload values
3. Build a CP-SAT model
4. Inject constraints for the selected payload
5. Attach the objective
6. Run the solver
7. Format the solution

### Family solver

The family solver can return multiple top solutions.

After it finds one solution, it adds a no-good constraint to forbid that exact architecture. Then it solves again. This allows it to produce several different feasible architectures instead of only one.

### Diagnostic solver

The diagnostic solver is used to understand feasibility.

It tests each bus class one by one:

1. Force the bus class
2. Run the solver
3. If feasible, report the selected tiers and margins
4. If infeasible, enumerate tier combinations outside CP-SAT to identify likely failure families

This is useful because it can explain why smaller bus classes fail.

For example, it may report:

- Mass closure failed
- Volume closure failed
- Solar power failed
- Battery capacity failed
- Downlink failed
- ADCS pointing failed
- Thermal rejection failed

---

## 5. Example study

### Selected case

For this explanation, use a Navigation mission:

- Mission family: Navigation
- Payload: a PNT augmentation payload such as `Ned-RF-daT-001`
- ROI: Global
- Revisit time: 48 hours

### What happens

The payload is resolved from the master Navigation payload database and converted into engineering numbers.

A PNT payload has:

- Non-trivial power demand
- Pointing requirement
- Real-time navigation/timing behavior
- High temperature stability requirement

The backend then derives requirements:

- The satellite must carry the payload mass
- The payload must fit in the bus volume
- The bus must provide enough average and peak power
- The communication subsystem must support the payload data rate
- The ADCS must satisfy pointing accuracy
- Thermal control must be enhanced if the payload is sensitive

### Likely subsystem behavior

The solver then tests possible architectures.

A small bus such as 1U or 2U may fail because it cannot provide enough mass capacity, volume, or power.

A 3U bus may also fail if total mass or power exceeds its limit.

A 6U bus is more likely to pass because it has more mass, power, and volume margin.

For subsystems:

- If the payload needs accurate pointing, the solver upgrades ADCS from Standard to Precise or better.
- If the payload data rate is moderate, S-band may be enough and cheaper than X-band.
- If the payload thermal class is sensitive, the solver selects Enhanced Thermal.
- If basic EPS and OBC satisfy the constraints, the solver keeps them basic to reduce cost.

### Why components are selected

The solver’s logic is constraint-first and cost-second:

1. It first removes impossible designs.
2. Then it chooses the lowest-cost feasible combination.

So if a basic component satisfies the requirement, it will usually be selected. If a requirement forces a stronger component, the solver upgrades only that component.

---

## 6. What the current solver is good at

The current solver is good for:

- Turning payload specifications into system-level requirements
- Checking feasibility against mass, power, volume, pointing, downlink, and thermal limits
- Choosing a consistent platform/subsystem architecture
- Returning margins and warnings
- Explaining selected components through Solver Trace

---

## 7. Current limitation

The main mission solver currently uses the large master databases for payloads, but it still uses a smaller internal subsystem catalog for bus and subsystem choices.

That means the payload side is richer than the subsystem side.

To make the solver more realistic, the next major improvement would be to add full subsystem master databases for:

- EPS
- ADCS
- OBC
- Communication
- Thermal
- Propulsion
- Structure / bus
- Radiation support

Then the solver could choose from a much larger set of commercial subsystem examples.

---

## 8. Recommended next improvement

Add a candidate-comparison trace.

For each subsystem domain, show:

- Selected candidate
- Feasible but rejected alternatives
- Infeasible alternatives
- Reason for rejection
- Reason for final selection

Example:

```json
{
  "domain": "comm",
  "selected": "S-band Downlink",
  "candidates": [
    {
      "name": "S-band Downlink",
      "status": "selected",
      "reason": "Meets required downlink and has lowest cost."
    },
    {
      "name": "X-band Downlink",
      "status": "feasible_not_selected",
      "reason": "Also feasible, but higher cost."
    },
    {
      "name": "Low-rate UHF",
      "status": "rejected",
      "reason": "Does not meet required downlink rate."
    }
  ]
}
```

This would make the Solver Trace page much clearer for thesis/demo purposes.
