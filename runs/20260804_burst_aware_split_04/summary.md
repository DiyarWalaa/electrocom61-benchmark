> **RELEASED SPLIT — cite this directory.** Promoted 2026-08-04, superseding
> `runs/20260803_corrected_split_02/`. The heading below still reads
> "(CANDIDATE)" because that is the word the script wrote at generation time;
> the run's numbers are untouched.
>
> `split_manifest.csv` here is the released assignment.
> `data/ElectroCom-61_corrected/` was built from it and verified in
> `runs/20260804_build_corrected_dataset_02/`.
>
> τ=15 s, scene ε=0.05, seed 20260804. 68 images moved. Sizes 1478/438/205
> held exactly. All 61 classes ≥5 instances in both valid and test. Zero
> test↔train near-duplicate pairs at every epsilon under both scorings.
>
> **valid↔train contamination is 1 pair (raw) / 3 pairs (aligned) at ε=0.05 in
> BOTH this split and the published one.** Those pairs are pre-existing in the
> published data; neither allocator created them and neither removed them. Do
> not read "zero contamination" as applying to all three cross-split
> relationships — it applies to test↔train.

# Burst-aware split (CANDIDATE)

Run directory: `20260804_burst_aware_split_04`  |  tau=15s  |  scene eps=0.05  |  seed=20260804

Candidate alternative to `runs/20260803_corrected_split_02`, which remains canonical. Whole bursts move together, so no group can straddle the split boundary.

## Headline comparison

| metric | corrected_split_02 | burst-aware (this run) |
|---|---|---|
| images moved | 64 | 68 |
| test<->train near-dup pairs, raw eps=0.05 | 2 | 0 |
| test<->train near-dup pairs, aligned eps=0.05 | 4 | 0 |
| classes below the bar | 0 | 0 |
| sizes held (1478/438/205) | yes | yes |

## Why the size constraint held or failed

To hold the sizes, each split must give back exactly as many images as it took, as WHOLE groups. A group can only be given back if removing it leaves every class at or above 5.

| split | images to return | pure groups in split | safe to remove | images available in safe groups | outcome |
|---|---|---|---|---|---|
| test | 15 | 32 | 30 | 59 | exact subset found |
| valid | 19 | 74 | 74 | 141 | exact subset found |

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

- atomic groups in total: **776**
- groups already straddling two splits before any move: **177** (left untouched; pre-existing, not created here)
- groups admitted: valid 18, test 13
- groups returned to train: valid 10, test 6

## What could make this misleading

- Whole-group movement prevents groups from straddling. It does NOT prevent two DIFFERENT groups from being near-duplicates of each other; the contamination table above is the check on that, not the group logic.
- tau=15s was chosen because it is the smallest swept value at which every rescued class has two qualifying groups. A larger tau would isolate duplicates better and cost more images.
- Scene components stand in for bursts among the untimestamped images. They group by appearance, not time, and are weaker.
- Moving more images than the baseline is not automatically worse: the two splits should be compared on contamination and on class coverage, with images-moved as context.

