\appendix

# Printer Calibration

This guide covers the essential calibration steps you should run before building or tuning a filament preset. Whether you are working with a single machine or a small farm, the goal is the same: establish a reliable baseline so that later parameter changes are meaningful.

In a multi-machine environment, run these steps on every unit and compare the results. Consistent calibration is what lets different printers produce matching parts. With a single machine, treat these steps as a one-time baseline that you can revisit when print quality drifts.

---

## Nozzle Inspection and Replacement

A worn or damaged nozzle makes every downstream calibration unreliable, so start here.

Measure the actual nozzle bore with pin gauges, plug gauges, or a microscope. The measured diameter should fall within **+15% / -5%** of the nominal size.

Inspect the exit edge for smoothness, burrs, residue, or partial clogs. If you see wear, eccentricity, or any foreign material, replace the nozzle before continuing.

---

## Machine Calibration

Run the printer's built-in calibration routine first. This typically includes XYZ alignment and Z-offset adjustment.

### Bed Mesh Compensation

- If the built-in routine already performs bed mesh compensation, no extra action is needed.
- If it does not, but the printer supports mesh bed leveling, run `G29` manually.
- If the printer has no mesh compensation support, level the bed by hand with feeler gauges or calipers. Match the four corners and the center as closely as possible. If the bed has local low spots, you can shim them with high-temperature tape or Kapton tape.

---

## Temperature Calibration

Clean any remaining filament from the nozzle, then heat it to the printer's rated maximum temperature.

Insert a thermocouple probe into the nozzle and read the actual temperature. Repeat the measurement at **200 °C** and record the difference.

### Acceptable Deviation

- More than **±2.5 °C** at 200 °C: recalibrate.
- More than **±3%** at the maximum temperature: recalibrate.

### How to Correct the Offset

- If you can access the firmware, adjust the temperature offset there.
- If the firmware is locked, apply the offset in your slicer instead.

---

## Extrusion Calibration

This procedure uses a 100 mm extrusion test. PolyLite PC is recommended because its amorphous structure and good thermal stability give more repeatable results than crystalline materials. Measure the filament diameter beforehand with calipers and confirm it is within the nominal range.

### Tools

- PolyLite PC filament
- Digital calipers
- A marker

### Prepare the Extruder

Clean the extruder and surrounding area. If the drive gears have old plastic buildup, remove the extruder and clean the gears so they grip reliably. After preheating, run a short purge to make sure the hot end and nozzle are clear.

### Load Filament and Preheat

Preheat the nozzle to the working temperature for the filament you are using. If another non-flexible filament is already loaded, preheat to its normal printing temperature instead. Load the calibration filament cleanly and make sure it feeds without contamination.

### Mark and Extrude

Send the calibration command or G-code to the printer over USB, SD card, USB drive, or Wi-Fi.

From the edge of the filament inlet, measure exactly **120 mm** outward and mark the filament clearly. This mark is your reference point.

Run the extrusion G-code, which commands the printer to extrude 100 mm of filament.

### Measure the Remaining Length

After extrusion stops, measure the remaining distance from the extruder inlet to your mark. Call this length **L_remaining**.

- If **L_remaining > 20 mm**, the printer extruded less than 100 mm. This is **under-extrusion**; increase the E-steps or flow factor.
- If **L_remaining < 20 mm**, the printer extruded more than 100 mm. This is **over-extrusion**; decrease the E-steps or flow factor.

### Calculate and Adjust

1. Actual extruded length:  
   **L_actual = 120 - L_remaining**
2. Extrusion accuracy:  
   **Accuracy (%) = (L_actual / 100) × 100%**

If the deviation exceeds **±3%**, adjust the E-steps or flow ratio and repeat the test until the accuracy is within tolerance.
