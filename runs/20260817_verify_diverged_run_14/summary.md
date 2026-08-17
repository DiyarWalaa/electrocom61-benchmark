# Diverged run: rtdetr_l_pub

Run directory: `20260817_verify_diverged_run_14`

RT-DETR-l on the published split at **lr0 = 0.01**, seed 0, Tesla P100-PCIE-16GB. Marked `diverged` in `master_results.csv`; never aggregated with the benchmark.

## Summary figures

| quantity | file | claimed | |
|---|---|---|---|
| stopped at epoch | `19` | `19` | PASS |
| training minutes | `43.7` | `43.7` | PASS |
| val mAP@50 | `0.0039` | `0.0039` | PASS |
| val mAP@50-95 | `0.0016` | `0.0016` | PASS |
| val classes evaluated | `45` | `45` | PASS |
| test mAP@50 | `0.0057` | `0.0057` | PASS |
| test mAP@50-95 | `0.0026` | `0.0026` | PASS |
| test classes evaluated | `46` | `46` | PASS |
| best epoch (derived) | `4` | `4` | PASS |

The JSON carries no `best_epoch` field. It is derived as the argmax of Ultralytics fitness (0.1*mAP@50 + 0.9*mAP@50-95) over the training curve.

## First NaN epoch, per loss column

| column | pass | first NaN | finite epochs after |
|---|---|---|---|
| `train/cls_loss` | train | 7 | none |
| `train/giou_loss` | train | 7 | none |
| `train/l1_loss` | train | 7 | none |
| `val/cls_loss` | val | 2 | 4 |
| `val/giou_loss` | val | 2 | 4 |
| `val/l1_loss` | val | 2 | 4 |

## Notes

- best epoch 4 + patience 15 = last epoch 19, so the stopping epoch corroborates the best epoch independently
- the VALIDATION loss terms first go NaN at epoch [2], well before the training terms at 7, and recover at epochs (4,). Any claim covering 'its three loss terms' without saying which pass is at best ambiguous.
- mAP@50 is ALSO exactly zero at epoch(s) [5], before divergence. Zero mAP is therefore not exclusive to the post-divergence regime, and cannot on its own be used to date the divergence.

## What could make this misleading

- `status: complete` in the JSON means the run finished without raising, NOT that it succeeded. It completed uselessly.
- The reported mAP figures come from a separate validation pass on `best.pt` (epoch 4), not from the training curve row for that epoch, so the two differ slightly and neither is wrong.
- Latency and complexity columns are empty for this run because the unified timing pass covered the ten benchmark checkpoints only.

