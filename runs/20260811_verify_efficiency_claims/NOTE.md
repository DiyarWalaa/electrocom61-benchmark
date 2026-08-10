# Superseded by `20260811_verify_efficiency_claims_02`

Do not cite this run. Nothing in it is wrong; it is incomplete in a way that
would have produced a misleading report.

## What it did

It expressed every per-session gap as a percentage of the **smaller** value of
the pair, and only that. On that basis the worst cross-session spread is
30.41%, and the prose's claim of "up to 23%" reads as a straightforward
understatement.

## Why that was not good enough

A gap between two numbers can be divided by the smaller, the larger, or the
mean, and at this magnitude the three answers differ by seven points:

    yolov9s   18.58 vs 24.23 ms   gap 5.65 ms
              of min  30.41%      of max  23.32%      of mean  26.40%

The prose's 23% is reproduced exactly by dividing by the larger. It is not an
understatement; it is a different and equally defensible convention. Reporting
"the claim is wrong, it is really 30%" would have been the misleading result
here, not the careful one.

`_02` computes all three denominators, identifies which one reproduces the
stated figure, and additionally establishes from its own columns that
`latency_by_arch.csv` -- the source of the 1.75% in the same paragraph --
divides by the **mean**. That is the finding worth reporting: two percentages
in one subsection resting on different bases.
