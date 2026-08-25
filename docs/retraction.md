# Retraction

**Applicable to:**

- All FDM printers.
- All non-foaming thermoplastic materials.

## Purpose

Determine the best retraction distance for the material on the target printer and process settings. The goal is to find the value that minimizes stringing and oozing without retracting so far that it causes clogging or under-extrusion, so the printed parts have clean surface quality and the process stays stable.

## Preparation

1. Enable **Developer Mode** in the slicer preferences.
2. Open the **Calibration** menu and select **Retraction Test**.
3. Set `Start retraction distance` to 0, `End retraction distance` to 2 for direct drive or 6 for Bowden, and `Step` to 0.1.

---

## Procedure

### Test Flow

1. **Parameter setup**: Confirm that temperature, cooling, maximum volumetric speed, and flow ratio are already set from previous calibration results.
2. **Print the model**: Print the Retraction Test.
3. **Inspect the model**: Look at the towers or test pieces and find the height range with the least stringing and no under-extrusion.
4. **Record**: Note the height index $n$ of the best-looking section (indices start at 0 from the bottom).
5. **Calculate retraction distance**:  
   $Retraction Distance = Start + Step \times n$

---

## Archiving

1. Mark the material name, test date, and the position / parameters of the best block on the test piece base with a marker.
2. Keep the physical sample for later re-inspection.

---

## Reference

[OrcaSlicer Wiki — Retraction Calibration](https://github.com/OrcaSlicer/OrcaSlicer/wiki/retraction-calib)
