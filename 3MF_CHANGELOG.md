# Polymaker Test Suite — 3MF Change Log

Because `.3mf` files are binary archives, Git cannot show meaningful diffs. This document records every intentional change to a `.3mf` test model so the repository history remains useful and auditable.

## How to use this template

Each time a `.3mf` file is added, replaced, or materially changed, append a new entry under **Change Log** using the template below.

## Change Log

### 2026-06-15 — Initialize 3MF change log

- **File:** `3MF_CHANGELOG.md`
- **Version:** `v1.0.0`
- **Date:** `2026-06-15`
- **Author:** `@Jingxi-Polymaker`
- **Change Type:** `Added`
- **Summary:** Initialize change log to track `.3mf` test model changes.
- **Details:**
  - Added `3MF_CHANGELOG.md` to document binary 3MF changes that Git cannot diff.
  - Includes entry template, file inventory table, and change type legend.
- **Validation:** N/A (documentation-only change)
- **Related Issue / PR:** initial commit
- **Notes:** First commit to the repository.

---

### Template (use for future entries)

- **File:** `filename.3mf`
- **Version:** `vX.Y.Z`
- **Date:** `YYYY-MM-DD`
- **Author:** `@github-username`
- **Change Type:** `Added` | `Modified` | `Removed` | `Replaced`
- **Summary:** One-line description of what changed and why.
- **Details:**
  - What geometry / parts / settings were affected.
  - Which printer, material, or profile version the model targets.
  - Any fixes for previous issues (warping, tolerances, support, etc.).
- **Validation:**
  - Slicer(s) and version used to verify the file opens correctly.
  - Print test result (pass / fail / pending).
- **Related Issue / PR:** `#123`
- **Notes:** Anything else a reviewer should know.

---

## File Inventory

| File Name | Current Version | Last Updated | Owner / Contact |
|-----------|-----------------|--------------|-----------------|
| `3MF_CHANGELOG.md` | `v1.0.0` | `2026-06-15` | `@Jingxi-Polymaker` |
| `All in one Test.3mf` | `v1.0.0` | `2026-06-15` | `@Jingxi-Polymaker` |

---

## Change Types

- **Added** — new file introduced to the suite.
- **Modified** — existing file updated (geometry, settings, profiles, thumbnails, etc.).
- **Removed** — file deleted from the suite.
- **Replaced** — file superseded by another; note the replacement file name.
