# Superseded by `20260812_verify_master_results_02`

Do not cite this run. Its two FAILs are retained because they are the record of
the guard working, not of a defect in the data.

## What it recorded

    [FAIL] RT-DETR-l published test mAP@50   expected 0.9171  found 0.0057 / 0.9171
    [FAIL] RT-DETR-l gflops_fused            expected 105.6   found 105.6 / None

## Why

This run happened immediately after `rtdetr_l_pub` was added to
`master_results.csv`. The structural checks -- added in the same change -- all
passed: the `inclusion` column was present, exactly ten rows were labelled
`benchmark`, the diverged run was labelled `diverged`, and
`ec61.load_benchmark_rows()` accepted the table.

The VALUE expectations were still reading the master table unfiltered. So a
lookup for "RT-DETR-l published" matched two rows -- the benchmark run at
0.9171 and the diverged run at 0.0057 -- and the existing
disagreement-across-rows check fired.

That check was doing exactly its job. The two runs are supposed to differ; the
error was asking a question that spanned both. `_02` filters the value
expectations through `ec61.load_benchmark_rows()` as well, and passes 17/17.

Worth keeping because it is the concrete demonstration that adding a row which
duplicates `(model, split_set)` breaks a consumer that indexes by that pair --
the failure mode the `inclusion` column exists to prevent.
