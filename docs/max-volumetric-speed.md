# Max Volumetric Speed (max-speed)

**Applicable to:**

- Rigid and semi-rigid plastics (flexible plastics require the S-path test)
- Most 3D printers
- Printers with Sparse infill acceleration $\ge 3000\;\text{mm/s}^2$

## Purpose

Find the maximum volumetric flow rate the hot end can reliably and consistently extrude per second. This prevents under-extrusion, voids, weak points, and uneven layers during high-speed printing, helping maintain print quality.

---

## Principle

Print speed is increased step by step, which raises the volumetric flow rate. Once the flow exceeds the hot end's melt limit, under-extrusion appears and the internal infill layers do not bond well, creating voids. After printing, hold the sample against a steady light source and check whether light passes through the internal crossing area. Light leakage means the extrusion was unstable at that speed. The last speed with no leakage is taken as the maximum reliable speed.

---

## Preparation

1. In the slicer's process settings, confirm **Sparse infill acceleration ≥ 3000 mm/s²**.
2. Edit the filament profile:
   - Disable "slow down for better cooling".
   - Set **Max volumetric speed = 500 mm³/s** to remove the slicer-side flow limit.
   - Set **printing temperature** and **cooling parameters** according to the previous test results.

---

## Procedure

1. **Model selection**: In the **Print Process Test 3MF** file, choose the **Max Volumetric Speed Test**.
2. **Print the model**: Pick a suitable speed model and print it on its own. (For example, PLA usually has a top speed around 200 mm/s, so for PLA drag the model labeled 200 onto an empty plate.)
3. **Preview check**: After slicing, verify that the **temperature**, **print speed**, and **infill** are set to grid, and that the **infill direction** is 90°.
4. **Inspection**: When the print is finished, hold the sample up to a stable light source and examine the **internal crossing area** for light leaks.
   - If light leaks through, mark that speed as NG.
   - If no light leaks, mark it as G.
   - Continue until an NG speed appears, then use the **previous speed with no NG** as the maximum printable speed.
5. **Record**: Mark the test part with a marker and record the print temperature.

---

## Volumetric Flow Calculation and Notes

### Slic3r-based Slicers

**Cross-sectional area formula**

$$A = m_{height} \times \Big(m_{width} - m_{height} \times (1 - 0.25\pi)\Big)$$

**Volumetric flow formula**

$$Q_{max} = v \times A \quad ({mm}^3/{s})$$

Where:

- $m_{height}$: layer height (mm)
- $m_{width}$: line width (mm)
- $v$: line speed (mm/s)

---

### Example (Slic3r-based)

Assume $m_{height} = 0.2$ mm, $m_{width} = 0.45$ mm, and $v_{ok} = 200$ mm/s:

1. Calculate the cross-sectional area:

$$A \approx 0.0814 { mm}^3/{mm}$$

2. Calculate the volumetric flow rate:

$$Q = 200 \times 0.0814 \approx 16.28 { mm}^3/\text{s}$$

---

### Non-Slic3r-based Slicers

- Read the **volumetric flow rate (mm³/s)** directly from the slicer preview or G-code analysis.
- Use the volumetric flow rate of the fastest no-NG level as $Q_{max}$; no extra calculation is needed.
