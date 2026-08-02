# Redundancy within the untimestamped `counter` family

- `counter` images with usable labels: **189**
- their actual directories: train=189, valid=0, test=0
- largest class-multiset bucket inside the family: 74 (MAX_BUCKET=600 never binds, so this is exhaustive)
- counter-vs-counter pairs scored: 4273

These images cannot leak into test -- they are all in train, and
`scene_signature.py` finds zero test images with a train twin at
every epsilon with low-information pairs excluded. What follows is
about TRAINING SET SIZE, not contamination.

## Counter vs counter: how many of the 189 have a twin among the other 188

| scoring | eps | excl_low | n_pairs | imgs_with_twin | components | multi_comps | largest_comp | redundant |
|---|---|---|---|---|---|---|---|---|
| raw | 0.01 | False | 0 | 0 | 189 | 0 | 1 | 0 |
| raw | 0.01 | True | 0 | 0 | 189 | 0 | 1 | 0 |
| raw | 0.02 | False | 0 | 0 | 189 | 0 | 1 | 0 |
| raw | 0.02 | True | 0 | 0 | 189 | 0 | 1 | 0 |
| raw | 0.05 | False | 14 | 23 | 176 | 10 | 4 | 13 |
| raw | 0.05 | True | 14 | 23 | 176 | 10 | 4 | 13 |
| aligned | 0.01 | False | 1 | 2 | 188 | 1 | 2 | 1 |
| aligned | 0.01 | True | 1 | 2 | 188 | 1 | 2 | 1 |
| aligned | 0.02 | False | 6 | 11 | 183 | 5 | 3 | 6 |
| aligned | 0.02 | True | 6 | 11 | 183 | 5 | 3 | 6 |
| aligned | 0.05 | False | 54 | 71 | 146 | 28 | 5 | 43 |
| aligned | 0.05 | True | 54 | 71 | 146 | 28 | 5 | 43 |

`components` counts distinct scenes, singletons included, so it is
the effective number of independent training images in this family.
`redundant` = 189 - components. Quote that, not `imgs_with_twin`:
three shots of one scene make 3 pairs and 3 images-with-a-twin but
only 2 redundant images.

Single linkage is transitive, so a large `largest_comp` may be a
chain through intermediates rather than one repeated scene. Check
`counter_components_aligned_excl_low.csv` before quoting a large one.

## Counter vs ANY train image (wider than the question asked)

| scoring | eps | excl_low | n_pairs | counter_imgs_with_train_twin |
|---|---|---|---|---|
| raw | 0.01 | False | 0 | 0 |
| raw | 0.01 | True | 0 | 0 |
| raw | 0.02 | False | 0 | 0 |
| raw | 0.02 | True | 0 | 0 |
| raw | 0.05 | False | 14 | 23 |
| raw | 0.05 | True | 14 | 23 |
| aligned | 0.01 | False | 1 | 2 |
| aligned | 0.01 | True | 1 | 2 |
| aligned | 0.02 | False | 6 | 11 |
| aligned | 0.02 | True | 6 | 11 |
| aligned | 0.05 | False | 54 | 71 |
| aligned | 0.05 | True | 54 | 71 |

No bucket exceeded MAX_BUCKET=600; this table is complete.

## Reconciling with the `71` in the scene_signature summary

- counter images in >=1 pair with ANYTHING, loose prefilter min(raw,aligned)<=0.05, low-info included: **71**
- same, restricted to counter-vs-counter: **71**

The scene_signature figure is an upper bound built on the loosest
epsilon, the kinder of the two scorings, and pairs with any
partner. The tables above are the strict readings of it.

