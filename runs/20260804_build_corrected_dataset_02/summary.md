# Corrected-split dataset build

Run directory: `20260804_build_corrected_dataset_02`

- manifest: `C:/research/electrocom61/runs/20260804_burst_aware_split_04/split_manifest.csv`
- destination: `C:/research/electrocom61/data/ElectroCom-61_corrected`
- source (unmodified): `C:/research/electrocom61/data/ElectroCom-61_v2`

## Verification

| check | measured | expected | result |
|---|---|---|---|
| image counts per split | 1478 / 438 / 205 | 1478 / 438 / 205 | PASS |
| copy loop intent matches disk | 1478 / 438 / 205 | same as disk | PASS |
| every image has a label | 0 missing | 0 | PASS |
| no orphan labels | 0 orphans | 0 | PASS |
| copies byte-identical to source | 0 mismatches | 0 | PASS |
| total instances | 12937 | 12937 | PASS |
| all 61 classes >= 5 in valid AND test | 61 of 61 | 61 | PASS |
| class ids within 0..60 | 0 out of range | 0 | PASS |

**All checks passed.**

## Per-class instance counts (from the copied labels)

| class_id | class_name | train | valid | test | total |
|---|---|---|---|---|---|
| 0 | 1-5-Volt-Battery | 94 | 109 | 8 | 211 |
| 1 | 3-3-Volt-Battery | 83 | 38 | 84 | 205 |
| 2 | 7-Segment-Display | 132 | 35 | 17 | 184 |
| 3 | 9-Volt-Battery | 150 | 5 | 5 | 160 |
| 4 | Arduino-Mega | 129 | 29 | 19 | 177 |
| 5 | Arduino-Nano | 84 | 98 | 12 | 194 |
| 6 | Arduino-Uno | 194 | 8 | 5 | 207 |
| 7 | BJT-Transistor | 113 | 89 | 27 | 229 |
| 8 | Bluetooth-Module | 235 | 6 | 8 | 249 |
| 9 | Breadboard | 130 | 31 | 20 | 181 |
| 10 | Bridge-Rectifier | 162 | 45 | 23 | 230 |
| 11 | Buck-Converter | 117 | 33 | 18 | 168 |
| 12 | Buzzer | 259 | 7 | 6 | 272 |
| 13 | Capacitor-10mf | 94 | 100 | 24 | 218 |
| 14 | Capacitor-470mf | 97 | 102 | 20 | 219 |
| 15 | DC-Motor | 57 | 31 | 83 | 171 |
| 16 | Diode | 246 | 9 | 10 | 265 |
| 17 | ESP32 | 182 | 5 | 5 | 192 |
| 18 | ESP32-CAM | 79 | 37 | 76 | 192 |
| 19 | FT-232-USB-Serial-Module | 60 | 31 | 82 | 173 |
| 20 | Film-Capacitor | 154 | 15 | 9 | 178 |
| 21 | Fuse | 157 | 11 | 8 | 176 |
| 22 | Fuse-Base | 150 | 19 | 6 | 175 |
| 23 | GSM-Module | 165 | 48 | 23 | 236 |
| 24 | Gas-Sensor | 204 | 10 | 7 | 221 |
| 25 | Heat-Sink | 162 | 7 | 6 | 175 |
| 26 | High-Voltage-Ceramic-Capacitor | 242 | 8 | 7 | 257 |
| 27 | Humidity-Sensor | 167 | 45 | 22 | 234 |
| 28 | IC-Base-14-Pin | 167 | 50 | 22 | 239 |
| 29 | IC-Base-28-Pin | 166 | 44 | 21 | 231 |
| 30 | IC-Chip | 317 | 12 | 10 | 339 |
| 31 | IGBT | 88 | 116 | 12 | 216 |
| 32 | IR-Sensor | 94 | 107 | 20 | 221 |
| 33 | Inductor | 276 | 7 | 10 | 293 |
| 34 | Keypad | 101 | 80 | 10 | 191 |
| 35 | LCD-Display | 165 | 7 | 5 | 177 |
| 36 | LDR-Sensor | 151 | 5 | 5 | 161 |
| 37 | LED-Light | 279 | 8 | 6 | 293 |
| 38 | Low-Voltage-Ceramic-Capacitor | 105 | 95 | 17 | 217 |
| 39 | MLC-Capacitor | 273 | 10 | 9 | 292 |
| 40 | MOSFET | 60 | 126 | 21 | 207 |
| 41 | Motion-Sensor | 162 | 48 | 19 | 229 |
| 42 | Motor-Driver | 167 | 5 | 5 | 177 |
| 43 | NTC-Thermistor | 114 | 95 | 13 | 222 |
| 44 | OLED-Display | 266 | 7 | 6 | 279 |
| 45 | Pin-Header | 61 | 97 | 13 | 171 |
| 46 | Push-Switch | 261 | 10 | 6 | 277 |
| 47 | RFID-Scanner | 143 | 5 | 5 | 153 |
| 48 | Raindrops-Module | 71 | 35 | 81 | 187 |
| 49 | Relay-Module | 159 | 45 | 24 | 228 |
| 50 | Resistor | 121 | 33 | 15 | 169 |
| 51 | Rocker-Switch | 91 | 78 | 12 | 181 |
| 52 | Servo-Motor | 161 | 6 | 7 | 174 |
| 53 | Soil-Moisture-Sensor | 73 | 91 | 20 | 184 |
| 54 | Sonar-Sensor | 223 | 7 | 5 | 235 |
| 55 | TCRT5000 | 115 | 32 | 18 | 165 |
| 56 | Tact-Switch | 86 | 104 | 22 | 212 |
| 57 | Taper-Potentiometer | 61 | 34 | 77 | 172 |
| 58 | Trimmer-Potentiometer | 161 | 47 | 20 | 228 |
| 59 | Water-Sensor | 165 | 44 | 21 | 230 |
| 60 | Zener-Diode | 111 | 106 | 21 | 238 |

## What could make this misleading

- These checks prove the tree MATCHES THE MANIFEST. They say nothing about whether the manifest is a good split. The leakage cost of this split is in `runs/20260803_corrected_split_02/summary.md` and travels with it.
- Class ids are inherited from v2. If a v2 label is wrong, it is copied here unchanged and wrong in the same way.
- >= 5 instances makes a class measurable, not well measured. Classes sitting near the floor still cannot support a confident per-class AP.
- The build copies; it does not deduplicate. Near-duplicate images identified in earlier runs are all still present.

