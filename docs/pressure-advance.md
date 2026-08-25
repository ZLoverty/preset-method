# Pressure Advance (pressure-advance)

**Applicable to:**

- Hard / semi-hard materials (PLA, PETG, PA-CF, etc.): use PA Tower.
- Flexible plastics (TPU, TPEE, etc.): use PA Pattern.
- Only for printers and firmware that support Pressure Advance / K-Factor.

## Purpose

Determine the optimal Pressure Advance value for the material on the target printer and process settings. The result provides a reliable reference for building a preset library and enabling consistent production runs.

---

## Preparation

1. Enable **Developer Mode** in the slicer preferences.
2. Open the **Calibration** menu and select **Pressure Advance Calibration**.
3. Choose **PA Tower** for rigid filaments or **PA Pattern** for flexible filaments.
4. Set `PA_start` to 0, `PA_end` to 1, and `PA_step` to 0.002.

## Procedure

### Hard and Semi-Hard Materials (PA Tower)

1. **Parameter setup**: Set temperature, cooling, maximum volumetric speed, and flow ratio based on previous calibration results.
2. **Print the model**: Print the PA Tower.
3. **Inspect the model**: Hold the tower up to a light and examine the front corners. Find the height where the corner is closest to a right angle and the transitions on both sides look even. Then check the back seam and find the height where it is flattest, without under-extrusion or over-extrusion.
4. **Record**: Note the best front-corner height index $n_1$ and the best back-seam height index $n_2$ (indices start at 0 from the bottom).
5. **Calculate PA**:  
   $PA = PA_{start} + PA_{step} \times n$ (where $n$ is the test height / step index)

### Flexible Plastics (PA Pattern)

1. **Parameter setup**: Set temperature, cooling, maximum volumetric speed, and flow ratio based on previous calibration results.
2. **Print the model**: Print the PA Pattern.
3. **Inspect the model**: Choose the line that is most uniform, with no breaks or bumps.
4. **Record**: Note the PA value for the best-performing region.

---

## Archiving

1. Mark the corresponding height on the test part with a marker.
2. Keep the physical sample for later re-inspection.

---

## Reference

[OrcaSlicer Wiki — Pressure Advance Calibration](https://github.com/SoftFever/OrcaSlicer/wiki/pressure-advance-calib)

---

## Figure

![Pressure advance measurement guide. The green gauge has a numbered scale on the left and a V-slot on the right. Red lines inside the V-slot correspond to positions 1, 2, 3, and 4. Lines 1, 2, and 3 align with the scale, while line 4 does not. This shows how to read the PA value from the V-slot alignment.](assets/pressure-advance-measurement.png)

1. PA too low
2. PA too high
3. Best PA
