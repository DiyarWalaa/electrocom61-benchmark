# Corrected-split dataset build

Run directory: `20260804_build_corrected_dataset`

- manifest: `C:/research/electrocom61/runs/20260803_corrected_split_02/split_manifest.csv`
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
| 0 | 1-5-Volt-Battery | 98 | 105 | 8 | 211 |
| 1 | 3-3-Volt-Battery | 88 | 38 | 79 | 205 |
| 2 | 7-Segment-Display | 131 | 36 | 17 | 184 |
| 3 | 9-Volt-Battery | 150 | 5 | 5 | 160 |
| 4 | Arduino-Mega | 129 | 29 | 19 | 177 |
| 5 | Arduino-Nano | 78 | 104 | 12 | 194 |
| 6 | Arduino-Uno | 189 | 12 | 6 | 207 |
| 7 | BJT-Transistor | 102 | 100 | 27 | 229 |
| 8 | Bluetooth-Module | 235 | 7 | 7 | 249 |
| 9 | Breadboard | 130 | 31 | 20 | 181 |
| 10 | Bridge-Rectifier | 162 | 45 | 23 | 230 |
| 11 | Buck-Converter | 117 | 33 | 18 | 168 |
| 12 | Buzzer | 255 | 8 | 9 | 272 |
| 13 | Capacitor-10mf | 90 | 104 | 24 | 218 |
| 14 | Capacitor-470mf | 86 | 111 | 22 | 219 |
| 15 | DC-Motor | 65 | 31 | 75 | 171 |
| 16 | Diode | 246 | 11 | 8 | 265 |
| 17 | ESP32 | 182 | 5 | 5 | 192 |
| 18 | ESP32-CAM | 82 | 37 | 73 | 192 |
| 19 | FT-232-USB-Serial-Module | 66 | 31 | 76 | 173 |
| 20 | Film-Capacitor | 148 | 19 | 11 | 178 |
| 21 | Fuse | 153 | 11 | 12 | 176 |
| 22 | Fuse-Base | 152 | 16 | 7 | 175 |
| 23 | GSM-Module | 164 | 48 | 24 | 236 |
| 24 | Gas-Sensor | 207 | 7 | 7 | 221 |
| 25 | Heat-Sink | 162 | 7 | 6 | 175 |
| 26 | High-Voltage-Ceramic-Capacitor | 245 | 6 | 6 | 257 |
| 27 | Humidity-Sensor | 167 | 45 | 22 | 234 |
| 28 | IC-Base-14-Pin | 167 | 50 | 22 | 239 |
| 29 | IC-Base-28-Pin | 165 | 44 | 22 | 231 |
| 30 | IC-Chip | 319 | 11 | 9 | 339 |
| 31 | IGBT | 90 | 111 | 15 | 216 |
| 32 | IR-Sensor | 89 | 112 | 20 | 221 |
| 33 | Inductor | 279 | 7 | 7 | 293 |
| 34 | Keypad | 88 | 91 | 12 | 191 |
| 35 | LCD-Display | 167 | 5 | 5 | 177 |
| 36 | LDR-Sensor | 149 | 6 | 6 | 161 |
| 37 | LED-Light | 277 | 10 | 6 | 293 |
| 38 | Low-Voltage-Ceramic-Capacitor | 98 | 102 | 17 | 217 |
| 39 | MLC-Capacitor | 274 | 8 | 10 | 292 |
| 40 | MOSFET | 64 | 122 | 21 | 207 |
| 41 | Motion-Sensor | 161 | 48 | 20 | 229 |
| 42 | Motor-Driver | 167 | 5 | 5 | 177 |
| 43 | NTC-Thermistor | 101 | 104 | 17 | 222 |
| 44 | OLED-Display | 264 | 10 | 5 | 279 |
| 45 | Pin-Header | 51 | 103 | 17 | 171 |
| 46 | Push-Switch | 262 | 8 | 7 | 277 |
| 47 | RFID-Scanner | 143 | 5 | 5 | 153 |
| 48 | Raindrops-Module | 74 | 35 | 78 | 187 |
| 49 | Relay-Module | 158 | 45 | 25 | 228 |
| 50 | Resistor | 118 | 33 | 18 | 169 |
| 51 | Rocker-Switch | 83 | 86 | 12 | 181 |
| 52 | Servo-Motor | 159 | 7 | 8 | 174 |
| 53 | Soil-Moisture-Sensor | 65 | 98 | 21 | 184 |
| 54 | Sonar-Sensor | 225 | 5 | 5 | 235 |
| 55 | TCRT5000 | 115 | 32 | 18 | 165 |
| 56 | Tact-Switch | 80 | 106 | 26 | 212 |
| 57 | Taper-Potentiometer | 65 | 34 | 73 | 172 |
| 58 | Trimmer-Potentiometer | 160 | 47 | 21 | 228 |
| 59 | Water-Sensor | 165 | 44 | 21 | 230 |
| 60 | Zener-Diode | 101 | 116 | 21 | 238 |

## What could make this misleading

- These checks prove the tree MATCHES THE MANIFEST. They say nothing about whether the manifest is a good split. The leakage cost of this split is in `runs/20260803_corrected_split_02/summary.md` and travels with it.
- Class ids are inherited from v2. If a v2 label is wrong, it is copied here unchanged and wrong in the same way.
- >= 5 instances makes a class measurable, not well measured. Classes sitting near the floor still cannot support a confident per-class AP.
- The build copies; it does not deduplicate. Near-duplicate images identified in earlier runs are all still present.

