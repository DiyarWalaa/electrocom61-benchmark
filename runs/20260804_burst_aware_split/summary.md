# Burst-aware split (CANDIDATE)

Run directory: `20260804_burst_aware_split`  |  tau=30s  |  scene eps=0.05  |  seed=20260804

Candidate alternative to `runs/20260803_corrected_split_02`, which remains canonical. Whole bursts move together, so no group can straddle the split boundary.

## Headline comparison

| metric | corrected_split_02 | burst-aware (this run) |
|---|---|---|
| images moved | 64 | 64 |
| test<->train near-dup pairs, raw eps=0.05 | 2 | 0 |
| test<->train near-dup pairs, aligned eps=0.05 | 4 | 0 |
| classes below the bar | 0 | 0 |
| sizes held (1478/438/205) | yes | **NO** -> 1458/438/225 |

Size constraint could not be met for: test (needed 20). Whole-group movement cannot adjust a count by one image, and no exact subset of returnable groups summed to the required total.

## Near-duplicate contamination, three ways

| state | scoring | eps | test<->train | valid<->train | valid<->test |
|---|---|---|---|---|---|
| published | raw | 0.01 | 0 | 0 | 0 |
| published | raw | 0.02 | 0 | 0 | 0 |
| published | raw | 0.05 | 0 | 1 | 0 |
| published | aligned | 0.01 | 0 | 0 | 0 |
| published | aligned | 0.02 | 0 | 0 | 0 |
| published | aligned | 0.05 | 0 | 3 | 0 |
| burst_aware | raw | 0.01 | 0 | 0 | 0 |
| burst_aware | raw | 0.02 | 0 | 0 | 0 |
| burst_aware | raw | 0.05 | 0 | 1 | 0 |
| burst_aware | aligned | 0.01 | 0 | 0 | 0 |
| burst_aware | aligned | 0.02 | 0 | 0 | 0 |
| burst_aware | aligned | 0.05 | 0 | 3 | 0 |

## Groups

- atomic groups in total: **460**
- groups already straddling two splits before any move: **120** (left untouched; pre-existing, not created here)
- groups admitted: valid 15, test 16
- groups returned to train: valid 4, test 0

## What could make this misleading

- Whole-group movement prevents groups from straddling. It does NOT prevent two DIFFERENT groups from being near-duplicates of each other; the contamination table above is the check on that, not the group logic.
- tau=30s was chosen because it is the smallest swept value at which every rescued class has two qualifying groups. A larger tau would isolate duplicates better and cost more images.
- Scene components stand in for bursts among the untimestamped images. They group by appearance, not time, and are weaker.
- Moving more images than the baseline is not automatically worse: the two splits should be compared on contamination and on class coverage, with images-moved as context.

