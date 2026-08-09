# Figures

Run directory: `20260809_make_figures_07`

## F1 — per-class instance counts (published split)

- source: `runs/20260802_class_date_provenance/class_split_counts.csv`
- outputs: `figures/f1_class_instance_counts.pdf`, `figures/f1_class_instance_counts.png` (300 dpi)

| quantity | value |
|---|---|
| n_classes | 61 |
| total_instances | 12937 |
| train_instances | 9188 |
| valid_instances | 2600 |
| test_instances | 1149 |
| zero_valid_plus_test | 15 |
| fewer_than_5_test | 22 |
| between_1_and_4_test | 7 |
| largest_class | IC-Chip (339) |
| smallest_class | RFID-Scanner (153) |
| figure_width_in | 3.5 |
| figure_height_in | 8.952 |

Classes with zero valid+test instances: `Inductor`, `LED-Light`, `MLC-Capacitor`, `OLED-Display`, `Push-Switch`, `Buzzer`, `High-Voltage-Ceramic-Capacitor`, `Bluetooth-Module`, `Sonar-Sensor`, `Gas-Sensor`, `LCD-Display`, `Motor-Driver`, `LDR-Sensor`, `9-Volt-Battery`, `RFID-Scanner`

Classes with 1-4 test instances: `IC-Chip`, `Diode`, `Arduino-Uno`, `ESP32`, `Fuse-Base`, `Heat-Sink`, `Servo-Motor`

## What could make this misleading

- Counts are annotation instances, not images. A class with many instances in few images is less diverse than the bar suggests; `imgs_*` columns in the source carry that.
- The published split is shown. Under the released burst-aware split every class has at least 5 instances in both valid and test, so this figure describes the problem, not the shipped state.
- Sorting is by total instances, which is dominated by train. A class high in the ordering can still be unevaluable.

## F5 — published vs corrected test accuracy

- source: `data/master_results.csv`
- outputs: `figures/f5_published_vs_corrected.{pdf,png}`
- rendered 3.50 x 5.40 in

| model | mAP@50 delta | mAP@50-95 delta | ratio |
|---|---|---|---|
| rtdetr-l | +2.73 | +1.19 | 0.44 |
| yolo26s | +4.06 | +1.88 | 0.46 |
| yolov9s | +2.74 | +1.23 | 0.45 |
| yolo11s | +3.92 | +1.03 | 0.26 |
| yolo12s | +4.27 | +1.75 | 0.41 |

### The gains shrink at higher IoU

mAP@50-95 gains run **+1.03 to +1.88 points** against **+2.73 to +4.27** for mAP@50 — roughly half, with the per-model ratio between 0.26 and 0.46.

The classes the corrected split makes evaluable are therefore **easy at IoU 0.5 but not uniformly easy at higher thresholds**. Detecting that they are present is most of the gain; localising them tightly is not.

### Near-tie structure, and how to phrase it

On mAP@50-95 both splits show the same shape: **yolo26s** clearly first, **yolo12s** clearly last, and the three intermediate models (yolo11s, yolov9s, rtdetr-l) spanning only **0.0023 corrected** and **0.0039 published**.

So the claim **"the ordering is identical across splits" overstates it**. The defensible statement is:

> The same model ranks first and last on both splits, while the three intermediate models are not separable at a single seed.

Use that phrasing in the writing phase. A single training run gives no variance estimate, and a 0.0023 span is far inside what a seed change would plausibly move.

## F6 — accuracy vs latency

- sources: `data/latency_by_arch.csv` + `data/master_results.csv`
- outputs: `figures/f6_accuracy_vs_latency.{pdf,png}`
- rendered 3.50 x 3.49 in

| model | latency p50 (ms) | pair gap | mAP@50-95 | GFLOPs | front |
|---|---|---|---|---|---|
| yolo11s | 13.680 | 0.24 | 0.6187 | 21.549 | yes |
| yolo26s | 14.645 | 0.05 | 0.6317 | 20.892 | yes |
| yolo12s | 18.945 | 0.23 | 0.6017 | 23.301 |  |
| yolov9s | 21.045 | 0.13 | 0.6186 | 26.855 |  |
| rtdetr-l | 47.210 | 0.12 | 0.6164 | 105.600 |  |

Pareto front: **yolo11s, yolo26s**. Noise floor **0.24 ms**, the largest gap between the two timed runs of any one architecture (yolo11s).

- `rtdetr-l` misses the front by **0.00220 mAP**, dominated by `yolo11s`, `yolo26s`, `yolov9s`.
- `yolo12s` misses the front by **0.01700 mAP**, dominated by `yolo11s`, `yolo26s`.
- `yolov9s` misses the front by **0.00010 mAP**, dominated by `yolo11s`, `yolo26s`.

`yolo11s` and `yolo26s` are the closest pair in latency at **0.96 ms**, 4.0 times the noise floor — separable, but not by much.

