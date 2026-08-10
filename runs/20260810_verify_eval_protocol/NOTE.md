# Superseded by `20260810_verify_eval_protocol_02`

Do not cite this run. It is retained because it is evidence of a real defect in
the first version of the script, not because its numbers are usable.

## What was wrong

This run located each run's `args.yaml` and `per_class.csv` only at the
flattened, run-slug-prefixed path used by eight of the ten runs:

    data/kaggle/artifacts/<run>/<run>_args.yaml

The two yolov9s runs kept Kaggle's original directory tree instead -- their
zips are the ones named `_artifacts_loose.zip` -- so their arguments live at

    data/kaggle/artifacts/<run>/runs/<run>/args.yaml

and they have no `per_class.csv` at all. Both were reported as missing, and the
threshold agreement in this run therefore covers **eight runs, not ten**.

The values happen to be the same in both runs. That is luck, not validation: a
claim that `conf`, `iou` and `max_det` are identical across all ten runs cannot
rest on a check that silently examined eight.

## What `_02` does differently

- `find_args_yaml()` tries both layouts before reporting a run as missing.
- The class-difference check reads `per_class_AP50_95` from the committed
  `results_<run>.json`, which exists for all ten runs, and uses `per_class.csv`
  only as an independent cross-check where the layout provides one.
