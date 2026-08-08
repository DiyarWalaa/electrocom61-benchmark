# Figures

Run directory: `20260808_make_figures_03`

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

Classes with zero valid+test instances: `Inductor`, `LED-Light`, `MLC-Capacitor`, `OLED-Display`, `Push-Switch`, `Buzzer`, `High-Voltage-Ceramic-Capacitor`, `Bluetooth-Module`, `Sonar-Sensor`, `Gas-Sensor`, `LCD-Display`, `Motor-Driver`, `LDR-Sensor`, `9-Volt-Battery`, `RFID-Scanner`

Classes with 1-4 test instances: `IC-Chip`, `Diode`, `Arduino-Uno`, `ESP32`, `Fuse-Base`, `Heat-Sink`, `Servo-Motor`

## What could make this misleading

- Counts are annotation instances, not images. A class with many instances in few images is less diverse than the bar suggests; `imgs_*` columns in the source carry that.
- The published split is shown. Under the released burst-aware split every class has at least 5 instances in both valid and test, so this figure describes the problem, not the shipped state.
- Sorting is by total instances, which is dominated by train. A class high in the ordering can still be unevaluable.

