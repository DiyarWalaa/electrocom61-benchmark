# Burst clustering and cross-split membership

Layers 0-2 only: no permutation null, no pixel comparison.

- images on disk: **2121**
- with a parseable timestamp (clustered): **1932**
- **excluded, no timestamp: 189**
  - family `counter`: 189
  - by split: train=189, valid=0, test=0
- timestamped images using the family fallback for their device key: **50**

The excluded images are unreachable by ANY timestamp method. They are covered by `scene_signature.py` instead.

## Test images sharing a burst with >=1 train image

SUPPORTING EVIDENCE, NOT A HEADLINE. Timestamp adjacency is a
proxy for near-duplication, not a measurement of it. The direct
label-geometry test in `scene_signature.py` finds zero test images
with a train twin at every epsilon once low-information pairs are
excluded, and that is the result that settles the leakage
question. The table below describes the capture schedule.

| keying | tau_s | n_clusters | n_crossing | largest | n_test_clustered | test_with_train | pct_test | n_valid_clustered | valid_with_train | pct_valid |
|---|---|---|---|---|---|---|---|---|---|---|
| csv_device | 3 | 1816 | 22 | 6 | 205 | 7 | 3.4 | 438 | 18 | 4.1 |
| csv_device | 5 | 1437 | 109 | 6 | 205 | 45 | 22.0 | 438 | 81 | 18.5 |
| csv_device | 10 | 864 | 186 | 19 | 205 | 83 | 40.5 | 438 | 206 | 47.0 |
| csv_device | 30 | 306 | 119 | 58 | 205 | 107 | 52.2 | 438 | 319 | 72.8 |
| csv_device | 60 | 127 | 72 | 64 | 205 | 117 | 57.1 | 438 | 396 | 90.4 |
| family_only | 3 | 1817 | 22 | 6 | 205 | 7 | 3.4 | 438 | 18 | 4.1 |
| family_only | 5 | 1438 | 109 | 6 | 205 | 45 | 22.0 | 438 | 81 | 18.5 |
| family_only | 10 | 866 | 186 | 19 | 205 | 83 | 40.5 | 438 | 206 | 47.0 |
| family_only | 30 | 314 | 120 | 58 | 205 | 107 | 52.2 | 438 | 319 | 72.8 |
| family_only | 60 | 134 | 72 | 64 | 205 | 117 | 57.1 | 438 | 396 | 90.4 |

`test_with_train` is the count of test IMAGES, not clusters.

Read the two keyings against each other: if `csv_device` and
`family_only` give similar numbers, the device-key choice does not
drive the result. If they diverge, the device attribution needs
resolving before the number can be quoted.

Note the direction of the tau effect: larger tau chains more
frames together, so crossing counts rise monotonically. A high
count at tau=60 with a low count at tau=3 means the frames are
near-adjacent-in-time but not a tight burst -- weaker evidence.
Read `gap_histogram.csv` and pick tau at the valley.

