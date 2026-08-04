# Tau sweep: can any tau give zero contamination AND frozen sizes?

Run directory: `20260804_burst_aware_tau_sweep`  |  seed 20260804  |  scene eps 0.05

Allocator imported from `burst_aware_split.py`; at tau=30 this sweep reproduces `runs/20260804_burst_aware_split_03`: **yes**.

## The answer

**tau = 15s** is the smallest value satisfying both conditions.

| tau | all 15 have >=2 groups | t<->tr raw .05 | t<->tr aligned .05 | zero at every eps | sizes after | sizes held | moved | classes short | satisfies both |
|---|---|---|---|---|---|---|---|---|---|
| 15 | yes | 0 | 0 | yes | 1478/438/205 | yes | 68 | 0 | **YES** |
| 20 | yes | 0 | 0 | yes | 1478/438/205 | yes | 78 | 0 | **YES** |
| 25 | yes | 0 | 0 | yes | 1478/438/205 | yes | 80 | 0 | **YES** |
| 30 | yes | 0 | 0 | yes | 1458/438/225 | NO | 64 | 0 | no |
| 35 | yes | 0 | 1 | no | 1454/438/229 | NO | 74 | 0 | no |
| 45 | yes | 0 | 0 | yes | 1448/438/235 | NO | 88 | 0 | no |
| 60 | yes | 0 | 1 | no | 1408/477/236 | NO | 70 | 0 | no |

## Why sizes fail or hold

`test images to return` is what the split owes back; `available` is how many sit in groups that can be removed without dropping a class below 5.

| tau | groups | straddling | test owes | test available | valid owes | valid available | classes short of 2 groups |
|---|---|---|---|---|---|---|---|
| 15 | 776 | 177 | 15 | 59 | 19 | 141 | - |
| 20 | 637 | 155 | 19 | 47 | 20 | 113 | - |
| 25 | 549 | 136 | 19 | 26 | 21 | 106 | - |
| 30 | 460 | 120 | 20 | 10 | 22 | 86 | - |
| 35 | 407 | 104 | 24 | 9 | 25 | 79 | - |
| 45 | 332 | 84 | 30 | 3 | 29 | 46 | - |
| 60 | 280 | 72 | 31 | 1 | 39 | 17 | - |

## What could make this misleading

- One seed. The allocator is greedy; a different seed explores a different corner and could hold sizes where this one fails. The sweep answers the question for seed 20260804.
- Feasibility is counted over groups lying wholly inside the train-only sessions, matching burst_feasibility. Groups that already straddle are excluded from the count.
- Zero contamination is measured on label geometry, which under-detects: an occluded component changes the class multiset and the pair is never compared.

