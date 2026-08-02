# Burst clustering and cross-split membership

Layers 0-2 only: no permutation null, no pixel comparison.

- images on disk: **2121**
- with a parseable timestamp (clustered): **1932**
- **excluded, no timestamp: 189**
  - family `counter`: 189
  - by split: train=189, valid=0, test=0
- timestamped images using the family fallback for their device key: **50**

The excluded images are unreachable by ANY timestamp method. They are covered by `scene_signature.py` instead.

## Headline: test images sharing a burst with >=1 train image

| keying | tau_s | n_clusters | n_crossing | largest | n_test_clustered | test_with_train | pct | valid_with_train |
|---|---|---|---|---|---|---|---|---|
| csv_device | 3 | 1816 | 22 | 6 | 205 | 7 | 3.4 | 18 |
| csv_device | 5 | 1437 | 109 | 6 | 205 | 45 | 22.0 | 81 |
| csv_device | 10 | 864 | 186 | 19 | 205 | 83 | 40.5 | 206 |
| csv_device | 30 | 306 | 119 | 58 | 205 | 107 | 52.2 | 319 |
| csv_device | 60 | 127 | 72 | 64 | 205 | 117 | 57.1 | 396 |
| family_only | 3 | 1817 | 22 | 6 | 205 | 7 | 3.4 | 18 |
| family_only | 5 | 1438 | 109 | 6 | 205 | 45 | 22.0 | 81 |
| family_only | 10 | 866 | 186 | 19 | 205 | 83 | 40.5 | 206 |
| family_only | 30 | 314 | 120 | 58 | 205 | 107 | 52.2 | 319 |
| family_only | 60 | 134 | 72 | 64 | 205 | 117 | 57.1 | 396 |

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

