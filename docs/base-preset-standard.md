# Base Preset Standard

This standard applies to every new or rebuilt FDM print process preset. It defines what a base preset is, what information it must carry, and how it should be named so that presets stay organized and traceable.

## Definition and Role

### What a Base Preset Is

A base preset is the starting process profile for a specific printer and material combination. It is meant to be a safe, reliable configuration that produces a successful print without advanced tuning, and it serves as the parent for all further optimization, such as max flow rate tests and retraction calibration.

### Where Base Presets Come From

- **Built-in generic profiles**: Derived from the "Generic" profiles in slicers such as OrcaSlicer or Bambu Studio.
- **Printer manufacturer defaults**: Default material configurations supplied by the printer manufacturer.
- **Conservative estimates**: When no reference exists, start from general polymer behavior, such as typical PLA temperatures.

### Why It Matters

- **Hardware validation**: It removes slicer-parameter uncertainty and helps confirm that the machine itself is in good physical condition.
- **Parent for derived presets**: Advanced profiles, such as high-speed or fine-detail modes, should inherit from the base preset.
- **Low-risk first print**: It prioritizes reliability over speed, giving a better chance of success on a new machine or material.

---

## Required Basic Information

Each base preset must include the metadata below. This is usually recorded in the profile header comments or in an accompanying readme.

### Identification and Source

- **Preset name**: A unique identifier that follows the naming convention, following the naming convention.
- **Compatible printer**: The exact printer model the preset has been validated on, such as `X1C` or `A1 Mini`.
- **Supplier**: The filament manufacturer, using its official English brand name, for example `Polymaker`.
- **Material type**: The material family and subtype, such as `PLA Basic` or `PETG CF`.
- **Density**: The material density in g/cm³.
- **Softening temperature**: Vicat softening point or heat deflection temperature.
- **Nozzle temperature**: Recommended hot-end temperature range.
- **Bed temperature**: Recommended heated bed temperature.
- **Chamber temperature**: Target chamber temperature for actively heated enclosures, or the steady-state chamber temperature for enclosed printers.

### Data Sources and Rules

- Physical parameters should come from the manufacturer's technical data sheet or internal material review.
- Use official English brand names and exact printer model names.
- Enter density and softening-point values directly from the data sheet or review.
- Use the recommended temperature ranges from the data sheet as the starting point. For warping-prone engineering materials such as ABS, ASA, PC, and PA, always specify a chamber temperature. If the data sheet does not provide one, note that the value is based on a general material standard.

---

## Test Parameters

These parameters are determined through calibration prints and then written into the preset.

- **Nozzle temperature**: Best printing temperature confirmed with a temperature tower.
- **Cooling parameters**: Fan speed settings, including auxiliary fan speed, confirmed with a cooling test.
- **Max volumetric speed**: The maximum extrusion rate the material can sustain at the chosen temperature.
- **Flow ratio**: The calibrated flow coefficient based on measured extrusion.
- **Pressure advance**: The K value determined with a pressure advance tower or pattern test.
- **Retraction settings**: Retraction length and speed from a retraction test.

### Sources and Rules

- At the start, carry over values from the "Generic" profile as the baseline.
- Update each value based on the standardized test results.
- Required measurements: nozzle temperature, cooling, max volumetric speed, flow ratio, and pressure advance. These must be filled in from actual tests.
- Optional measurement: retraction. Test this only when stringing or related defects appear, and adjust as needed.
