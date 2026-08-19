# Thesis figures

Publication-ready figures derived from the implemented CubeSat Mission Configurator architecture.

## Files and suggested captions

1. `figure_01_system_architecture.svg` / `.png`
   - **Suggested caption:** System architecture of the mission-driven CubeSat configurator, showing the separation between the immersive React user interface, FastAPI engineering services, CP-SAT optimization layer, and catalog-based engineering data sources.

2. `figure_02_mission_workflow.svg` / `.png`
   - **Suggested caption:** End-to-end workflow from mission intent and payload definition to requirement derivation, constellation analysis, discrete subsystem optimization, screening, and traceable design output.

3. `figure_03_cpsat_model.svg` / `.png`
   - **Suggested caption:** Conceptual formulation of the CP-SAT subsystem-selection model, including discrete design variables, one-hot selection rules, coupled engineering feasibility constraints, preference-weighted optimization, and reported design evidence.

## Recommended usage

- Use the SVG files in LaTeX or other vector-capable publishing software for the sharpest output.
- Use the PNG files in Microsoft Word. They are exported at 3200 × 1800 pixels.
- Keep the captions in the thesis text rather than embedding longer descriptions into the figures.

## Regeneration

From the repository root:

```powershell
node docs/thesis_figures/generate_figures.mjs
node docs/thesis_figures/export_png.mjs
```

The figures use a 16:9 canvas and remain fully editable as SVG/XML.
