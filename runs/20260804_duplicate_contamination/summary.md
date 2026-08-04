# Near-duplicate contamination: published vs corrected split

Addendum to `runs/20260803_corrected_split_02`. Run directory: `20260804_duplicate_contamination`

## What this measures, and what it does not

**Near-duplicate contamination** -- two images show the same scene, judged from annotation geometry. That is the only thing measured here.

**Temporal adjacency** -- two images were captured close together in time -- is a DIFFERENT measurement, reported in `runs/20260803_corrected_split_02/summary.md` and in `runs/20260802_burst_clusters`. Images seconds apart need not be near-duplicates, and near-duplicates need not be adjacent in time. The two must never be merged into one word.

## Reconciliation with Stage 1

The published-split figures must reproduce `runs/20260802_scene_signature` exactly. They do.

| scoring | eps | stage1 pairs | here | stage1 test~train | here | stage1 valid~train | here | agree |
|---|---|---|---|---|---|---|---|---|
| aligned | 0.01 | 3 | 3 | 0 | 0 | 0 | 0 | yes |
| aligned | 0.02 | 13 | 13 | 0 | 0 | 0 | 0 | yes |
| aligned | 0.05 | 85 | 85 | 0 | 0 | 3 | 3 | yes |
| raw | 0.01 | 1 | 1 | 0 | 0 | 0 | 0 | yes |
| raw | 0.02 | 4 | 4 | 0 | 0 | 0 | 0 | yes |
| raw | 0.05 | 26 | 26 | 0 | 0 | 1 | 1 | yes |

## Three-way breakdown, low-information pairs excluded

Cross-split near-duplicate PAIRS. `excl_low_info=True` throughout, which is the row Stage 1 says to quote.

**raw scoring**

| eps | split | test<->train | valid<->train | valid<->test | all cross-split |
|---|---|---|---|---|---|
| 0.01 | published | 0 | 0 | 0 | 0 |
| 0.01 | corrected | 0 | 0 | 0 | 0 |
| 0.02 | published | 0 | 0 | 0 | 0 |
| 0.02 | corrected | 1 | 0 | 0 | 1 |
| 0.05 | published | 0 | 1 | 0 | 1 |
| 0.05 | corrected | 2 | 1 | 0 | 3 |

**aligned scoring**

| eps | split | test<->train | valid<->train | valid<->test | all cross-split |
|---|---|---|---|---|---|
| 0.01 | published | 0 | 0 | 0 | 0 |
| 0.01 | corrected | 1 | 0 | 0 | 1 |
| 0.02 | published | 0 | 0 | 0 | 0 |
| 0.02 | corrected | 1 | 0 | 0 | 1 |
| 0.05 | published | 0 | 3 | 0 | 3 |
| 0.05 | corrected | 4 | 3 | 0 | 7 |

## The corrected sentence

The published split had **zero test<->train near-duplicate pairs at every epsilon under both scorings** -- Stage 1's finding, reproduced here. It did NOT have zero cross-split pairs overall: at eps=0.05 it carries 1 valid<->train pairs under raw scoring and 3 under aligned.

The corrected split at eps=0.05 carries 2 test<->train and 1 valid<->train pairs under raw scoring (4 and 3 under aligned). At eps=0.02 and eps=0.01 the corresponding counts are in the tables above.

Quote the three columns separately. A single "cross-split pairs" number mixes test contamination, which biases the headline metric, with valid contamination, which biases model selection -- different consequences that should not share a row.

## Coverage

- images: **2121**
- distinct class-multiset buckets: **595**
- buckets compared: 293; pairs examined: 32822; buckets skipped: 0
- pairs retained for scoring (below the loosest epsilon under at least one scoring): 213
- cross-split pairs under the corrected split, all epsilons and both scorings: 81

## What could make this misleading

- The method UNDER-detects by construction. Pairs are only considered when their class multisets match exactly, so one occluded component in one frame makes a genuine duplicate invisible. Every count here is a floor.
- Annotation geometry is a proxy for visual similarity. Two different scenes laid out identically score as duplicates; the same scene re-annotated differently does not.
- `low_information` pairs (<= 2 boxes) are excluded from the headline because a centre match is cheap to achieve by chance with few boxes. They are still in the CSV with excl_low_info=no.
- This says nothing about whether the corrected split is a good split. It prices ONE axis of cost.

