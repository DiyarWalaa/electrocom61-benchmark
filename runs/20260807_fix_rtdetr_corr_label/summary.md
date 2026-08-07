# Corrected the split label on the RT-DETR-l corrected run

Run directory: `20260807_fix_rtdetr_corr_label`

`C:/research/electrocom61/data/kaggle/results_rtdetr_l_corr.json`

```diff
- "split_set": "published"
+ "split_set": "corrected"
```

| | |
|---|---|
| field | `split_set` |
| before | `published` |
| after | `corrected` |
| sha256 before | `c9067041f79b679f2a603fc5e2a00069054eda1b35bfcc24c1474ea5dd246760` |
| sha256 after | `f58caeb78eb947fd50c53cbe559e14c79593e173ccff4ae5532339261189580e` |
| other fields changed | none (asserted) |

## Evidence checked before editing

- `val.classes_evaluated` = **61**
- `test.classes_evaluated` = **61**

Only the corrected split evaluates all 61 classes. The published split leaves 15 classes with zero instances in both valid and test and 16 with none in valid (`runs/20260802_class_date_provenance`), so a genuinely published run reports at most 46. The file contradicted itself, and resolving that contradiction is what licensed the edit.

Corroborated by the artifact CSVs: this run's `per_class.csv` holds 123 lines (61 + 61 + header) against the published RT-DETR run's 92 (45 + 46 + header).

## What could make this misleading

- The script proves the file was self-contradictory. It does not independently prove which dataset the GPU actually read; that rests on classes_evaluated being a faithful record of the evaluation.
- `args.yaml` cannot corroborate: both RT-DETR runs point at the same generic `/kaggle/working/electrocom61.yaml`, whose contents differed between sessions but were not captured.
- Only `split_set` was changed. If the same session mislabelled anything else, this script neither detects nor fixes it.

