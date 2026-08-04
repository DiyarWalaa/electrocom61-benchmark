# SUPERSEDED — do not cite this run

Canonical run: `runs/20260804_burst_feasibility_02/`.

Note added 2026-08-04, after the run. The files beside it are exactly as the
run produced them.

## Why

The verdict function conflated two different situations. A class with **zero**
groups in a regime was labelled `single_group`, the same label used for a class
genuinely confined to one shooting session.

That mislabelled `LED-Light` and `OLED-Display`, which have no timestamped
bursts at all because they appear only among the untimestamped `counter`
images. This run therefore reported them as unavoidable when in fact they are
simply absent from the timestamped regime — and the scene-component regime
rescues both.

The corrected run separates `absent_from_regime` from `single_group` and adds a
combined verdict across both regimes. Its conclusion is the opposite of this
one's on those two classes: **no class is genuinely unavoidable**.

The underlying group counts in `class_group_counts.csv` here are correct; only
the `verdict` column was wrong.
