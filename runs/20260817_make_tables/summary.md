# Tables

Run directory: `20260817_make_tables`

7 LaTeX booktabs tables under `tables/`, one file each.

- `tables/t1_unevaluable_classes.tex`
- `tables/t2_split_properties.tex`
- `tables/t3_training_config.tex`
- `tables/t4_main_results.tex`
- `tables/t5_efficiency.tex`
- `tables/t6_latency_breakdown.tex`
- `tables/t7_allocation_deviation.tex`

## Sources

- `runs/20260802_class_date_provenance/never_evaluated_classes.csv`
- `runs/20260802_class_date_provenance/class_split_counts.csv`
- `runs/20260802_class_date_provenance/date_split_summary.csv`
- `runs/20260804_build_corrected_dataset_02/class_counts_built.csv`
- `runs/20260804_build_corrected_dataset_02/config.json`
- `runs/20260804_burst_aware_split_04/split_manifest.csv`
- `runs/20260804_burst_aware_split_04/config.json`
- `runs/20260804_burst_aware_split_04/moves.csv`
- `runs/20260804_burst_aware_split_04/contamination_comparison.csv`
- `data/config_provenance.csv`
- `data/master_results.csv`
- `data/latency_by_arch.csv`
- `runs/20260809_split_ratio_by_group_03/split_ratio_by_group.csv`

## What could make these misleading

- T2 quotes the RELEASED split. `runs/20260804_duplicate_contamination` describes the superseded image-level split and reports 2 raw / 4 aligned test-train pairs where the released split reports 0 / 0. This script asserts the per-class counts it uses were built from the released manifest before quoting them.
- T4 is per split and T5 is per architecture. Accuracy depends on the split; latency does not.
- T1 counts annotation instances, not images. Both columns are given because a class with many instances in few images is less diverse than its instance count suggests.
- T7's nominal 70/20/10 is inferred from the aggregate, not documented by the dataset authors. If they intended another ratio every deviation in it shifts. The deviations are also real-valued rather than rounded to whole images, so a row can read $-0.8$ for an allocation no integer split could have improved on.

