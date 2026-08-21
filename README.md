# Polymaker Filament Preset Tuning Suite

This repository is a **Polymaker filament presets tuning document**. It exists
to help anyone tune better filament presets — and to share the domain knowledge
and methods behind those presets.

Filament presets are not the whole story. This is the same test-driven workflow
Polymaker uses internally to develop presets, refined and tested by our team
for more than a year. We are now open-sourcing it so the community, other
manufacturers, and makers everywhere can use it, improve it, and share their
own knowledge with us.

We are deeply grateful to everyone who has shared open-source tools, public
data, and documented know-how — this work builds on yours.

## Contents

- [Polymaker Filament Preset Tuning Suite](#polymaker-filament-preset-tuning-suite)
  - [Contents](#contents)
  - [About](#about)
  - [Calibration Pipeline](#calibration-pipeline)
  - [Documentation](#documentation)
  - [Test Model](#test-model)
  - [Credits](#credits)
  - [Contributing](#contributing)

## About

This repository documents the methodology Polymaker uses to develop filament
presets. Each preset parameter is validated through a physical test so the
final result balances print speed, surface quality, dimensional behavior, and
part strength.

Use this suite as a repeatable workflow: start from a mechanically sound
printer, run the calibration tests in order, record the results, and verify the
final preset with the included test model.

## Calibration Pipeline

Run the tests in this order. Each stage locks one variable before the next
stage begins.

1. **Cooling** — identify fan thresholds for geometry, bridging, and strength.
2. **Temperature** — define the usable thermal window for the material.
3. **Volumetric Flow** — find the maximum reliable extrusion rate.
4. **Flow Ratio** — tune the extrusion multiplier.
5. **Pressure Advance** — compensate for melt-stream inertia.
6. **Retraction** — reduce stringing and travel artifacts.

Start with the [entry guide](docs/entry.md) for the full workflow overview.

## Documentation

- [`docs/entry.md`](docs/entry.md) — start here for the pipeline overview and
  topic links.
- [`docs/printer-calibration.md`](docs/printer-calibration.md) — prepare the
  printer mechanically and verify extrusion.
- [`docs/base-preset-standard.md`](docs/base-preset-standard.md) — define
  preset naming, metadata, and source rules.
- [`docs/cooling.md`](docs/cooling.md) — calibrate cooling behavior.
- [`docs/temperature-tower.md`](docs/temperature-tower.md) — tune the material
  temperature range.
- [`docs/max-volumetric-speed.md`](docs/max-volumetric-speed.md) — determine
  maximum volumetric speed.
- [`docs/flow-ratio.md`](docs/flow-ratio.md) — calibrate flow ratio.
- [`docs/pressure-advance.md`](docs/pressure-advance.md) — tune pressure
  advance.
- [`docs/retraction.md`](docs/retraction.md) — run the retraction test.
- [`docs/overview.md`](docs/overview.md) — review the high-level workflow
  diagram.

## Test Model

`All in one Test.3mf` is the final verification model for the workflow. Print
it after completing the calibration pipeline to check the finished preset under
a combined test case.

Because `.3mf` files are binary assets, intentional changes to the model should
be recorded in [`3MF_CHANGELOG.md`](3MF_CHANGELOG.md).

## Credits

This project is possible because the 3D-printing community has already shared
so many useful tools, models, and calibration ideas. Thank you to the creators
and maintainers below for helping make better printer tuning accessible to more
people.

| Credit | What we learned from it | Source |
| --- | --- | --- |
| [#3DBenchy by CreativeTools and Daniel Norée][benchy] | A shared benchmark model for testing real printer behavior. | [CC0 1.0 Universal / Public Domain][benchy-license] |
| [Autodesk x Kickstarter FDM 3D Printer Assessment][autodesk-fdm] | A structured FDM printer assessment model and benchmarking approach. | [Apache-2.0][autodesk-license] |
| [The Torture Toaster by Clockspring][torture-toaster] | A practical tolerance, overhang, bed-adhesion, and moving-assembly test. | [CC BY-NC 4.0][torture-toaster] |
| [Improved Flow Ratio Calibration v3 by jimcorner][flow-ratio-model] | A clear visual approach for comparing flow-ratio changes. | [Creative Commons Attribution][flow-ratio-model] |
| [OrcaSlicer][orcaslicer] | Calibration tools, slicer workflows, and open community development. | [GNU AGPL-3.0][orcaslicer-license] |
| [Klipper][klipper] | Firmware concepts and pressure-advance calibration reference. | [GNU GPL-3.0][klipper-license] |
| [Bambu Studio][bambustudio] | Slicer workflow reference and auto-cooling documentation. | [GNU AGPL-3.0][bambustudio-license] |
| [PrusaSlicer][prusaslicer] | Slicer lineage, calibration ideas, and preset conventions inherited by the wider ecosystem. | [GNU AGPL-3.0][prusaslicer-license] |
| [Slic3r][slic3r] | The volumetric-flow cross-section formula used in max-speed calibration. | [GNU AGPL-3.0][slic3r-license] |
| [Marlin Firmware][marlin] | Firmware concepts and bed-mesh/leveling references. | [GNU GPL-3.0][marlin-license] |
| The broader open-source 3D-printing community | Decades of shared slicers, firmware, calibration models, documentation, and forum knowledge that make reproducible filament tuning possible. | — |


## Contributing

Contributions are welcome, especially improvements to test procedures,
slicer-specific notes, documentation clarity, and credit/license accuracy.
Please open an issue or pull request with the context for the change and any
supporting test results or source links.

<!-- markdownlint-disable MD013 -->

[benchy]: https://www.3dbenchy.com/
[benchy-license]: https://www.3dbenchy.com/license/
[autodesk-fdm]: https://github.com/kickstarter/kickstarter-autodesk-3d
[autodesk-license]: https://github.com/kickstarter/kickstarter-autodesk-3d/blob/master/LICENSE.txt
[flow-ratio-model]: https://makerworld.com/en/models/189543-improved-flow-ratio-calibration-v3
[klipper]: https://github.com/Klipper3d/klipper
[klipper-license]: https://github.com/Klipper3d/klipper/blob/master/COPYING
[orcaslicer]: https://github.com/OrcaSlicer/OrcaSlicer
[orcaslicer-license]: https://github.com/OrcaSlicer/OrcaSlicer/blob/main/LICENSE.txt
[torture-toaster]: https://www.printables.com/model/60985-the-torture-toaster
[bambustudio]: https://github.com/bambulab/BambuStudio
[bambustudio-license]: https://github.com/bambulab/BambuStudio/blob/master/LICENSE
[prusaslicer]: https://github.com/prusa3d/PrusaSlicer
[prusaslicer-license]: https://github.com/prusa3d/PrusaSlicer/blob/master/LICENSE
[slic3r]: https://github.com/slic3r/Slic3r
[slic3r-license]: https://github.com/slic3r/Slic3r/blob/master/LICENSE
[marlin]: https://github.com/MarlinFirmware/Marlin
[marlin-license]: https://github.com/MarlinFirmware/Marlin/blob/bugfix-2.1.x/LICENSE

<!-- markdownlint-enable MD013 -->
