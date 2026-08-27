# Flow Ratio (flow-ratio)

> References: [Bambu Studio Flow Rate Calibration](https://wiki.bambulab.com/en/software/bambu-studio/calibration_flow_rate) | [Reddit Guide](https://www.reddit.com/r/BambuLab/comments/1astmkp/easy_to_follow_flow_ratio_calibration/)

**Applicable to:**

- All materials
- Most 3D printers

---

## Purpose

This test uses a systematic experiment to find the best flow ratio for a given filament and printer combination. It prints a series of calibration patches with increasing flow ratios and evaluates their top-surface quality, correcting the difference between the slicer's theoretical extrusion and the actual physical extrusion.

After calibration, the flow ratio will:

1. **Improve surface quality**: Remove top-surface ripples, blob protrusions, and nozzle drag marks caused by over-extrusion, and fix gaps, unclosed lines, and rough surfaces caused by under-extrusion.
2. **Maintain dimensional accuracy**: Keep solid infill density and wall thickness within specification and control dimensional error.
3. **Improve process stability**: Establish an accurate flow baseline, which is a necessary prerequisite for tuning advanced parameters such as Pressure Advance.

---

## Principle

This test follows the single-variable rule. Using the slicer's modifier function, it prints an array of test blocks with a graded range of flow ratios. The top surface of each block is compared to judge the extrusion deviation:

- **Over-extrusion**: The surface looks rough; adjacent fill lines squeeze together and form ridges or waves.
- **Under-extrusion**: The surface looks loose; visible gaps remain between adjacent fill lines or the lines do not bond well.
- **Optimal**: The surface is flat and dense, with no obvious ridges or gaps, and feels smooth.

The test uses a two-step approach: a wide-range **Rough Tune** followed by a narrow-range **Fine Tune**, so the best flow ratio can be found efficiently and accurately.

---

## Variable Definitions

- $F_{\text{Default}}$: the initial flow ratio set for the filament (usually recommended as 1.0).
- $F_{\text{RoughTuned}}$: the intermediate flow ratio determined during the rough-tune stage.
- $F_{\text{FineTuned}}$: the final optimal flow ratio determined during the fine-tune stage.
- $\lambda$: the flow multiplier percentage marked on the test model (for example, 5 means +5%, i.e. 1.05×).

---

## Preparation

1. **Filament preparation**: Make sure the filament is dry; moisture can create bubbles that disturb surface inspection.
2. **Parameter settings**: Set **temperature**, **print speed**, and **cooling parameters** according to the previous test results. Enable **forced cooling** and **slow down for better cooling**.

---

## Procedure

### Rough Tune Stage

1. **Parameter setting**: Set the filament flow ratio to the initial value $F_{\text{Default}}$ (usually 1.0).
2. **Model selection**: In the **Print Process Test 3MF** file, choose **Flow Ratio Rough Tune**.
3. **Inspection**: Check whether the top surface shows raised arcs:
   - If **all models show raised arcs**, the starting flow is too high. Reduce the flow by **16%** (i.e. $F_{\text{New Default}} = F_{\text{Default}} \times (100\% - 16\%)$) and repeat.
   - If **none of the models show raised arcs**, the flow is too low. Increase the flow by **4%** (i.e. $F_{\text{New Default}} = F_{\text{Default}} \times (100\% + 4\%)$) and repeat.
   - Continue until the result contains both blocks with raised arcs and blocks without raised arcs.
4. **Calculation and recording**:
   - Record the base flow ratio $F_{\text{Default}}$ used.
   - Find the **first test block that shows raised arcs** and note its marked multiplier $\lambda_{\text{Rough}}$.
   - Calculate the rough-tuned flow ratio: $F_{\text{RoughTuned}} = F_{\text{Default}} \times \lambda_{\text{Rough}}$
   - Example: if $F_{\text{Default}} = 1.0$ and $\lambda_{\text{Rough}} = +5$, then $F_{\text{RoughTuned}} = 1.05$.

### Fine Tune Stage

1. **Update parameter**: Set the filament flow ratio to $F_{RoughTuned}$.
2. **Model selection**: In the **Print Process Test 3MF** file, choose **Flow Ratio Fine Tune**.
3. **Inspection**: Check the top surface for raised arcs:
   - Find the **first test block with no raised arcs** (the smoothest and most fully filled one) and note its marked multiplier $Multiplier_{Fine}$.
4. **Calculation and recording**:
   - Record this model's flow ratio as $F_{FineTuned}$ (formula: $F_{FineTuned} = F_{RoughTuned} \times Multiplier_{Fine}$).
5. **Save**: Write $F_{FineTuned}$ into the filament profile.

---

## Results Recording

$F_{FineTuned}$ = **optimal extrusion flow ratio**

- Store the test samples and mark them with the date and material batch if possible.

---

## Attached Image

![Extrusion test result showing two patches. The left patch is labeled "Optimal" and has a smooth surface with no obvious defects. The right patch is labeled "Too large" and shows a larger extrusion shape with visible depressions.](assets/flow-ratio-test-samples.png)
