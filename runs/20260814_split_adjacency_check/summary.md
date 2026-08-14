# Temporal adjacency across the split boundary

Run directory: `20260814_split_adjacency_check`  |  tau=15 s

Same-camera pairs captured within 15 s, counted as cross-split under the published assignment (the directory on disk) and under the released corrected assignment (`runs\20260804_burst_aware_split_04\split_manifest.csv`).

- images: **2121**; timestamped: **1932**; untimestamped and therefore OUT OF SCOPE: **189**

### Keying: `csv_device`

- same-camera pairs within 15 s: **1969** (all-pairs), **1306** (consecutive only)

| definition | state | total_pairs | cross_split | test<->train | train<->valid | test<->valid |
|---|---|---|---|---|---|---|
| all-pairs | published | 1969 | 556 | 159 | 312 | 85 |
| all-pairs | corrected | 1969 | 556 | 159 | 312 | 85 |
| consecutive | published | 1306 | 364 | 103 | 205 | 56 |
| consecutive | corrected | 1306 | 364 | 103 | 205 | 56 |

### Keying: `family_only`

- same-camera pairs within 15 s: **1963** (all-pairs), **1302** (consecutive only)

| definition | state | total_pairs | cross_split | test<->train | train<->valid | test<->valid |
|---|---|---|---|---|---|---|
| all-pairs | published | 1963 | 555 | 159 | 311 | 85 |
| all-pairs | corrected | 1963 | 555 | 159 | 311 | 85 |
| consecutive | published | 1302 | 364 | 103 | 205 | 56 |
| consecutive | corrected | 1302 | 364 | 103 | 205 | 56 |

## Verdict

| keying | definition | identical pair sets | created by allocator | removed by allocator |
|---|---|---|---|---|
| `csv_device` | all-pairs | **yes** | 0 | 0 |
| `csv_device` | consecutive | **yes** | 0 | 0 |
| `family_only` | all-pairs | **yes** | 0 | 0 |
| `family_only` | consecutive | **yes** | 0 | 0 |

## What could make this misleading

- Adjacency is not similarity. Two frames three seconds apart can show different scenes if the photographer moved on; two frames of the same scene can be minutes apart. This measure and the label-geometry one in `runs/20260804_duplicate_contamination/` fail in opposite directions, which is the only reason running both is informative.
- The 189 untimestamped images cannot appear in any count here. Whatever adjacency exists among them is invisible to this script.
- A pre-existing cross-split pair is not evidence against the allocator. The published split already separates frames inside a burst; the question this run answers is whether the corrected split separates ANY THAT THE PUBLISHED ONE DID NOT.
- tau is fixed at 15 s to match the released split. A different tau gives a different pair population and different counts.
