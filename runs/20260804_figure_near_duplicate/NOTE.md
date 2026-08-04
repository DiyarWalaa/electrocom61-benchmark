# SUPERSEDED — do not cite this run

Canonical run: `runs/20260804_figure_near_duplicate_02/`.

This note was added on 2026-08-04, after the run. The two files beside it
(`config.json`, `per_box_centre_shift.csv`) are exactly as the run produced
them and have not been altered.

## Why

This run rendered a first version of `figures/near_duplicate_pair.png` that had
three defects, all found by looking at the output:

1. **Wrong signs.** Both panels printed the same per-box shift signs. The shift
   is measured left → right, so the right-hand panel must negate it; as
   rendered, the figure stated that each image was displaced in the same
   direction from the other, which is impossible.
2. **Caption overflow.** The closing caption ran off both edges of the canvas
   and was cut mid-sentence.
3. **Label collision.** The `Fuse` and `Diode` labels printed on top of each
   other, their boxes' top edges being about 10 px apart.

`per_box_centre_shift.csv` in this directory is unaffected by all three — it
records the A → B shift, which is correct and identical to `_02`'s. Only the
rendered figure was wrong.

`figures/near_duplicate_pair.png` was overwritten by the `_02` run, so the
defective image no longer exists on disk. This note is the only record that it
did.
