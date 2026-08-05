# Split verification sheet

Run directory: `20260805_figure_verification_sheet_02`

Output: `figures/split_verification_sheet.png`

- pairs examined (same class multiset): **32822**
- cross-split pairs: **13737** (test<->train 4860, valid<->train 6928, valid<->test 1949)
- low-information cross-split pairs excluded: **95** (77 of them scored below column A's last row)
- buckets skipped as too large: 0

## test<->train

- pairs sharing a class multiset: **4860** (4837 non-low-information)
- qualifying as near-duplicates at any epsilon (<= 0.05): **0**
- closest test<->train pair: **0.0515**, which is 3% above the loosest threshold. The margin is thin, not comfortable.
- low-information test<->train pairs excluded: 23

## What could make this misleading

- Only pairs with identical class multisets are compared. An occluded component changes the multiset and the pair is never scored, so absence from this sheet is not absence of duplicates.
- Distance is annotation geometry, not pixels. Two different scenes laid out alike score as similar; the same scene re-annotated differently does not.
- Low-information pairs are excluded from the ranking. They are in `excluded_low_information.csv` and can be inspected there.
- A thin visual difference is not proof of independence. The sheet supports the contamination tables; it does not replace them.

