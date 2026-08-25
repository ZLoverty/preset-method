# Introduction

This guide presents the exact experimental workflows we use at Polymaker to calibrate our official filament presets. Each topic below links to a dedicated document with the full procedure.

Our goal is not a permanent, unchangeable ruleset, but a rigorous, physics-driven baseline that you can use to unlock maximum speed, flawless surface finishes, and structural integrity from your materials.

## Calibration Pipeline

We enforce a sequential order because each completed test locks in a baseline variable for the next. Changing the sequence changes the output — polymer processing variables are deeply inter-related.

| Step | Topic | Description |
|------|-------|-------------|
| 1 | [Cooling](cooling.md) | Establish part-cooling fan thresholds ($Fan_{\text{min}}$, $Fan_{\text{max}}$, $Layer_{\text{min}}$, $Layer_{\text{max}}$) |
| 2 | [Temperature Tower](temperature-tower.md) | Map the optimal thermal window for the filament |
| 3 | [Max Volumetric Speed](max-volumetric-speed.md) | Find the maximum extrusion rate before under-extrusion |
| 4 | [Flow Ratio](flow-ratio.md) | Calibrate the extrusion multiplier for accurate output |
| 5 | [Pressure Advance](pressure-advance.md) | Compensate for melt-stream inertia at high acceleration |
| 6 | [Retraction](retraction.md) | Eliminate stringing without inducing jamming |

## Supporting Documents

- [Printer Calibration](printer-calibration.md) — mechanical and extrusion calibration before tuning
- [Base Preset Standard](base-preset-standard.md) — naming conventions and metadata requirements
- [Workflow Overview](overview.md) — high-level flow diagram of the full development process

## Starting Point

All calibration starts from a baseline. Use the official recommended print conditions on the material packaging or engineering data sheet. If unavailable, select the generic preset built into your slicer (e.g., Generic PLA, Generic ABS).
