# Vision.md — CubeSat Mission Configurator

## Project Vision

Build a mission-driven **CubeSat and constellation configurator** that helps users move from a high-level mission idea to a technically grounded preliminary spacecraft architecture.

The platform should feel like a premium modern product on the front end, while being driven by transparent engineering logic and optimization on the back end.

It is **not** just a subsystem picker.  
It is a **mission design assistant** that connects:

- mission goals
- payload needs
- region of interest
- revisit requirements
- orbit / constellation estimation
- subsystem sizing and selection
- cost / margin / feasibility reporting

The result should be a tool that allows a user to describe **what mission they want to achieve**, and receive a **credible CubeSat architecture** assembled from commercial off-the-shelf subsystem options.

---

## Core Purpose

The purpose of this project is to create a configurator that can:

1. accept mission-driven inputs from a user
2. translate them into engineering requirements
3. estimate constellation and orbit needs
4. select feasible CubeSat subsystems from COTS catalogs
5. generate a structured mission report

This tool should support both:
- **exploration** for non-expert users
- **traceable technical reasoning** for engineering users

---

## Strategic Goal

Create a configurator that combines the usability of a polished commercial space product with the flexibility and transparency of a research-grade engineering tool.

The long-term goal is to make early-stage mission design:
- faster
- more consistent
- more explainable
- more data-driven
- less dependent on manual subsystem trade studies

---

## Product Positioning

This system sits between:

- a **visual mission wizard**
- a **preliminary spacecraft design tool**
- a **catalog-driven optimization engine**

It should guide the user from concept to candidate architecture without requiring them to manually understand every subsystem interaction.

At the same time, it must remain technically defensible and suitable for academic, research, and engineering use.

---

## Main User Promise

A user should be able to say:

> “I want a mission for this objective, over this region, with this revisit time.”

And the system should answer:

> “Here is a technically grounded CubeSat / constellation concept, with bus size, payload fit, subsystem choices, orbit recommendation, and feasibility summary.”

---

## Mission Families

To keep the experience simple and scalable, the configurator will organize the mission ontology into **three top-level mission families**:

### 1. Remote Sensing
Examples:
- hyperspectral
- multispectral
- VHR optical
- thermal imaging
- SAR
- custom confidential payload

### 2. IoT and Communication
Examples:
- IoT store-and-forward
- communication relay
- broadband communications
- optical communications
- secure communications
- custom confidential payload

### 3. Navigation
Examples:
- PNT augmentation
- AIS / ADS-B tracking related payloads
- RF navigation experiments
- timing / navigation payloads
- custom confidential payload

These three families simplify a broad ontology into a frontend structure that users can understand quickly, while still allowing extension later.

---

## My Payload Concept

The configurator must support a **confidential synthetic payload mode** called **My Payload**.

This is not a catalog payload.  
It is a user-defined payload object for cases where the payload is proprietary, classified, confidential, or simply not represented in the database.

### My Payload inputs
- payload name
- external length
- external width
- external height
- mass
- average power
- peak power
- optional data rate
- optional pointing requirement
- optional thermal requirement
- optional storage requirement
- optional onboard processing need

### Why it matters
This allows the configurator to still:
- estimate bus size
- allocate subsystem budgets
- size power and storage
- evaluate packaging fit
- run optimization

without requiring the user to disclose the payload identity.

---

## Product Principles

### 1. Mission-first, not component-first
The user should start from mission objectives, not by manually browsing hardware.

### 2. Engineering transparency
Every major decision should be explainable through traces, assumptions, or warnings.

### 3. Optimization over heuristics
Subsystem selection should be driven by a formal solver such as **CP-SAT**, not only by greedy logic.

### 4. Modular architecture
Constellation logic, subsystem sizing, optimization, reporting, and UI should be separable modules.

### 5. Scalable taxonomy
The system must start simple but allow new payload classes and mission families to be added later.

### 6. Premium user experience
The frontend should feel immersive, modern, dark, visual, and high-quality.

### 7. Original backend logic
The system may be inspired by reference configurators for user experience, but all engineering logic must be our own.

---

## Functional Vision

The intended workflow is:

1. **Select mission family**
2. **Select payload type or My Payload**
3. **Define region of interest or global coverage**
4. **Set mission parameters**
5. **Derive requirements**
6. **Estimate orbit / constellation**
7. **Optimize subsystem selection**
8. **Generate result and downloadable report**

This creates a guided user journey from abstract mission need to concrete architecture proposal.

---

## Backend Vision

The backend should act as an **engineering reasoning engine**.

### It should perform:
- input validation
- payload normalization
- requirement derivation
- bus size candidate evaluation
- constellation / orbit estimation
- subsystem optimization
- radiation awareness checks
- report assembly

### Target backend stack
- FastAPI
- Pydantic schemas
- OR-Tools CP-SAT
- JSON catalog loaders
- pytest-tested modules
- Dockerized deployment

---

## Frontend Vision

The frontend should be a **high-quality mission wizard**.

### Desired qualities
- visually immersive
- dark premium interface
- smooth transitions
- strong typography
- clear step-by-step flow
- interactive map / globe support
- result pages that feel presentation-ready

### Frontend should prioritize
- clarity for non-experts
- confidence for expert users
- strong visual hierarchy
- responsive state-driven flows
- no unnecessary engineering clutter on first use

### Target frontend stack
- React
- TypeScript
- Vite
- route-based wizard flow
- Playwright-tested interactions

---

## Optimization Vision

The solver should not simply pick arbitrary parts.

It should choose subsystem combinations that satisfy:
- payload-driven requirements
- mass limits
- volume limits
- power limits
- data-rate needs
- pointing needs
- thermal needs
- compatibility constraints
- optional cost preferences

### Why CP-SAT
CP-SAT is chosen because it can:
- enforce hard engineering constraints
- balance soft objectives
- support explainable selection logic
- outperform simple greedy approaches in constrained combinatorial selection problems

---

## Constellation Vision

The configurator should eventually become capable of sizing not only a satellite, but a **mission architecture**.

This includes:
- recommended orbit family
- altitude candidates
- inclination candidates
- revisit-driven satellite count
- orbital plane distribution
- global vs regional coverage reasoning

### v1 philosophy
Start with an explainable approximation model.

### Long-term philosophy
Upgrade later toward higher-fidelity mission analysis and propagation without breaking the outer system architecture.

---

## Data Vision

The database should represent a structured, extensible library of commercial off-the-shelf subsystem options.

### Core subsystem domains
- structure
- ADCS
- EPS
- OBC / data handling
- communications
- thermal
- propulsion
- payloads
- pricing
- radiation metadata

### Data quality goals
- normalized units
- consistent naming
- explicit constraints
- performance metadata
- traceable source references where possible
- easy extension with new vendors or products

---

## Bus Size Vision

The configurator should distinguish between:

### Official standard CubeSat sizes
- 1U
- 1.5U
- 2U
- 3U
- 6U
- 12U

### Commercially common extensions
- 8U
- 16U

This keeps the system realistic and aligned with both standards practice and market reality.

---

## Trust and Explainability Vision

The system should never behave like a black box.

For every solved architecture, the user should be able to inspect:
- which requirements were derived
- why a bus size was selected
- why a subsystem was selected
- what assumptions were used
- what constraints were tight
- what warnings remain
- where uncertainty still exists

This is especially important for research, thesis work, engineering review, and future MBSE integration.

---

## Output Vision

The final output should not just be a JSON response.  
It should be a **decision-ready mission summary**.

### Output should include
- selected mission family
- payload summary
- region of interest
- mission parameters
- constellation estimate
- orbit assumptions
- bus/platform summary
- selected subsystem set
- totals for mass, power, volume, and cost
- margins and warnings
- trace summary
- downloadable mission report

---

## Testing Vision

The project should be built with regression protection from the start.

### Testing layers
- unit tests for backend modules
- API tests for orchestration endpoints
- Playwright tests for frontend user journeys
- validation tests for schemas and input edge cases
- infeasible-case tests for optimization robustness

The goal is to keep the system stable while adding more catalogs, formulas, and mission modes.

---

## Deployment Vision

The application should be easy to run and demo.

### Deployment goals
- local Dockerized startup
- backend and frontend container separation
- repeatable environment setup
- easy transition to cloud hosting later

This allows the project to be used for:
- thesis demonstrations
- lab use
- engineering presentations
- future collaborative development

---

## Long-Term Vision

Over time, this platform can evolve from a configurator into a broader **space mission design environment**.

Possible future directions:
- MBSE integration
- more detailed power and ADCS sizing
- higher-fidelity orbit propagation
- design comparison mode
- multi-objective optimization
- uncertainty and sensitivity analysis
- mission trade study dashboards
- collaborative design sessions
- automated report generation for proposal workflows

---

## Success Criteria

This project is successful if it can:

1. guide a user through a mission design flow cleanly
2. convert payload and mission needs into subsystem requirements
3. produce a plausible CubeSat architecture from real catalog data
4. explain its decisions clearly
5. support confidential payload entry
6. estimate constellation needs at a useful preliminary level
7. generate a polished output report
8. remain extensible for deeper engineering development later

---

## One-Sentence Vision

**Build a mission-first CubeSat configurator that transforms user mission intent into an explainable, optimization-driven spacecraft and constellation concept using real subsystem catalogs and a premium interactive interface.**
