# Temperature Tower

**Applicable to:**

- Rigid plastics (PLA, PETG, ABS, PA, etc.)
- Most FDM 3D printers

---

## 1. Purpose

1. Find a reasonable print-temperature range for the filament.
2. Use the result to set a suitable **nozzle temperature** and **recommended nozzle-temperature range**, reducing stringing, cracking, and warping while improving accuracy and detail.

---

## 2. Principle

`M104` commands are inserted between layers to change the nozzle temperature. By comparing stringing, bridging, overhang quality, and surface detail across the different temperature bands, a reasonable temperature range can be determined and the optimal print temperature selected.

---

## 3. Preparation

1. Dry the filament thoroughly.
2. Edit the filament profile: set the **nozzle temperature** to the highest printable temperature for the material, configure the fan thresholds according to the results of the cooling calibration, enable **keep fan always on**, disable **slow down print for better cooling**, and disable **force cooling for overhangs/bridges**.

---

## 4. Procedure

1. **Model selection**: In the **process test 3MF** file, select the **temperature tower test** model.
2. **Temperature settings**: Set the **nozzle temperature** in the filament profile to the highest printable temperature for the material. After slicing, insert an `M104 Sxx` command every 50 layers to lower the temperature by 10 °C. (For example, if the highest PLA print temperature is 250 °C, add `M104 S240` at layer Z=50, `M104 S230` at Z=100, and so on.)
3. **Preview check**: After slicing, confirm that the **temperature**, **print speed**, and **cooling** settings match the intended values.
4. **Observation and selection**: At each temperature band, check the maximum overhang angle before failure, whether bridges sag, how severe stringing is, and whether any collapse occurs.
5. **Record**:
   - **Overhang**: Choose the lowest temperature among the four overhang angles that does not curl.
   - **Stringing**: Choose the temperature with the least stringing in each layer.
   - **Bridging**: Choose the temperature with the least sag in each layer.
   - **Final selection**: Combine the overhang, stringing, and bridging results. If several temperatures perform equally well, choose the highest one to preserve mechanical strength.
