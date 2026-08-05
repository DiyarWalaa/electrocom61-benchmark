# Consecutive counter-number pairs across the released split

Run directory: `20260805_consecutive_counter_pairs`

Reads the released burst-aware tau=15 split. **Changes nothing.**

## Counts

| quantity | value |
|---|---|
| counter-family images | 189 |
| counter range | 5126 - 5323 |
| repeated counter values | 0 |
| pairs differing by exactly 1 | 187 |
| of those, in the SAME split | 174 |
| of those, **split apart** | **13** |
| split apart AND never compared (different class multiset) | **3** |
| split apart AND flagged as duplicates (<= 0.05, low-info excluded) | 0 |

## By relationship

| relationship | split apart | comparable | never compared | flagged as duplicate | closest | median |
|---|---|---|---|---|---|---|
| test<->train | 3 | 2 | 1 | 0 | 0.0599 | 0.5723 |
| valid<->train | 9 | 7 | 2 | 0 | 0.0508 | 0.1597 |
| valid<->test | 1 | 1 | 0 | 0 | 0.2828 | 0.2828 |

## Every consecutive pair that is split apart

| counters | A | split | B | split | relationship | same multiset | score |
|---|---|---|---|---|---|---|---|
| 5151/5152 | IMG_5151 | TRAIN | IMG_5152 | VALID | valid<->train | yes | 0.1224 |
| 5152/5153 | IMG_5152 | VALID | IMG_5153 | TRAIN | valid<->train | yes | 0.1597 |
| 5188/5189 | IMG_5188 | TRAIN | IMG_5189 | VALID | valid<->train | yes | 0.4006 |
| 5189/5190 | IMG_5189 | VALID | IMG_5190 | TRAIN | valid<->train | yes | 0.0508 |
| 5214/5215 | IMG_5214 | TRAIN | IMG_5215 | VALID | valid<->train | yes | 0.2682 |
| 5215/5216 | IMG_5215 | VALID | IMG_5216 | TRAIN | valid<->train | yes | 0.0697 |
| 5233/5234 | IMG_5233 | TRAIN | IMG_5234 | VALID | valid<->train | **no** | **not comparable** |
| 5234/5235 | IMG_5234 | VALID | IMG_5235 | TRAIN | valid<->train | **no** | **not comparable** |
| 5240/5241 | IMG_5240 | TRAIN | IMG_5241 | VALID | valid<->train | yes | 0.3540 |
| 5241/5242 | IMG_5241 | VALID | IMG_5242 | TEST | valid<->test | yes | 0.2828 |
| 5243/5244 | IMG_5243 | TEST | IMG_5244 | TRAIN | test<->train | **no** | **not comparable** |
| 5268/5269 | IMG_5268 | TRAIN | IMG_5269 | TEST | test<->train | yes | 0.0599 |
| 5269/5270 | IMG_5269 | TEST | IMG_5270 | TRAIN | test<->train | yes | 0.5723 |

## What this does and does not establish

- Consecutive counter numbers mean the camera wrote two files in sequence. That makes a burst LIKELY, not certain: a photographer can rearrange a scene between two shutter presses, and the counter would not know.
- The `never compared` column is the important one. Those pairs have no distance under this method at all, because scene_signature only compares images with identical class inventories. They are absent from every contamination count in this repository -- not scored as safe, simply never looked at.
- A pair scoring above eps was judged not-a-duplicate by label geometry. Geometry is a proxy; two frames of one scene with a moved component score far apart while looking nearly identical to a person.
- Counter numbers are not globally ordered across devices. All 189 images here are one family, so adjacency is meaningful within it, but a gap in the sequence may mean a deleted frame rather than a session boundary.

