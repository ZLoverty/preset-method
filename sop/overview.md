# Filament Preset Development Workflow

The diagram below shows the full calibration and tuning workflow used to develop a filament preset.

![Complete filament preset development workflow, starting with printer calibration and moving through base preset setup, basic information, cooling, temperature tower, max flow rate, flow ratio, pressure advance, basic parameter fill, print evaluation, and feature-specific tests before exporting the final preset.](assets/calibration-pipeline-workflow.png)

The workflow begins by calibrating the printer itself, then builds a base preset, fills in verified parameters from a series of focused tests, evaluates the results on print models, runs any feature-specific tests that are needed, and finally exports the finished preset. Each step supplies data for the next, so the preset is built on measured behavior rather than guesswork.
