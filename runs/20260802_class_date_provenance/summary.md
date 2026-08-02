# Class coverage vs capture date

Run directory: `20260802_class_date_provenance`

Tests whether the never-evaluated classes are **session-confined** (only photographed on dates that landed entirely in train) or merely **rare**.

## Inputs as measured

- images on disk: **2121** (train 1478, valid 438, test 205)
- annotation instances parsed: **12937**
- images with no label file: **0**
- classes declared in data.yaml: **61**
- CSV rows joined / unjoined: 2071 / 50

## Externally reported figures vs this dataset

The 15/16 figures come from a run against Roboflow **v5**; this archive is Roboflow **v9**. Recomputed here:

| quantity | externally reported | measured here | agree? |
|---|---|---|---|
| classes with 0 instances in valid AND test | 15 | 15 | yes |
| classes with 0 instances in valid | 16 | 16 | yes |
| untimestamped (counter) images | 189 | 189 | yes |
| train-only capture dates | 20240219, 20240220 | 20240219, 20240220 | yes |

Classes with 0 instances in test: **15**. Classes absent from all three splits: **0**.

## The untimestamped images

`<untimestamped:counter>` bucket: **189 images** (train 189, valid 0, test 0). Train-only: **yes**.

These carry no capture time, so they cannot be placed on the session timeline. They are counted as a confined bucket only if measured to be train-only.

## Hypothesis verdicts

For each class with zero instances in both valid and test:

| verdict | n classes | meaning |
|---|---|---|
| session_confined | 15 | every date it appears on is train-only -- supports the hypothesis |
| rarity | 0 | appears on dates that DO reach valid/test -- hypothesis does not explain it |
| mixed | 0 | both kinds of date present |
| no_annotations | 0 | no instances anywhere in the dataset |

| class_id | class_name | verdict | inst_train | imgs_train | dates |
|---|---|---|---|---|---|
| 3 | 9-Volt-Battery | session_confined | 160 | 159 | 20240220 |
| 8 | Bluetooth-Module | session_confined | 249 | 179 | 20240220 |
| 12 | Buzzer | session_confined | 272 | 206 | 20240220 |
| 24 | Gas-Sensor | session_confined | 221 | 180 | 20240219;<untimestamped:counter> |
| 26 | High-Voltage-Ceramic-Capacitor | session_confined | 257 | 200 | 20240220 |
| 33 | Inductor | session_confined | 293 | 188 | 20240220 |
| 35 | LCD-Display | session_confined | 177 | 177 | 20240220 |
| 36 | LDR-Sensor | session_confined | 161 | 79 | 20240219 |
| 37 | LED-Light | session_confined | 293 | 184 | <untimestamped:counter> |
| 39 | MLC-Capacitor | session_confined | 292 | 81 | 20240219 |
| 42 | Motor-Driver | session_confined | 177 | 175 | 20240219;20240220 |
| 44 | OLED-Display | session_confined | 279 | 189 | <untimestamped:counter> |
| 46 | Push-Switch | session_confined | 277 | 177 | 20240220 |
| 47 | RFID-Scanner | session_confined | 153 | 153 | 20240220 |
| 54 | Sonar-Sensor | session_confined | 235 | 190 | 20240219;<untimestamped:counter> |

## Test-set instance counts

Classes with **fewer than 5** test instances: **22 of 61**.

| fewer than | n classes | pct of 61 |
|---|---|---|
| 1 | 15 | 24.6% |
| 2 | 17 | 27.9% |
| 3 | 20 | 32.8% |
| 4 | 21 | 34.4% |
| 5 | 22 | 36.1% |
| 10 | 25 | 41.0% |
| 20 | 37 | 60.7% |

Twenty lowest test counts:

| class_id | class_name | inst_test | imgs_test | inst_total |
|---|---|---|---|---|
| 3 | 9-Volt-Battery | 0 | 0 | 160 |
| 8 | Bluetooth-Module | 0 | 0 | 249 |
| 12 | Buzzer | 0 | 0 | 272 |
| 24 | Gas-Sensor | 0 | 0 | 221 |
| 26 | High-Voltage-Ceramic-Capacitor | 0 | 0 | 257 |
| 33 | Inductor | 0 | 0 | 293 |
| 35 | LCD-Display | 0 | 0 | 177 |
| 36 | LDR-Sensor | 0 | 0 | 161 |
| 37 | LED-Light | 0 | 0 | 293 |
| 39 | MLC-Capacitor | 0 | 0 | 292 |
| 42 | Motor-Driver | 0 | 0 | 177 |
| 44 | OLED-Display | 0 | 0 | 279 |
| 46 | Push-Switch | 0 | 0 | 277 |
| 47 | RFID-Scanner | 0 | 0 | 153 |
| 54 | Sonar-Sensor | 0 | 0 | 235 |
| 6 | Arduino-Uno | 1 | 1 | 207 |
| 25 | Heat-Sink | 1 | 1 | 175 |
| 16 | Diode | 2 | 2 | 265 |
| 17 | ESP32 | 2 | 2 | 192 |
| 30 | IC-Chip | 2 | 2 | 339 |

## What could make this misleading

- A `session_confined` verdict is **consistent with** the hypothesis, not proof of it. Capture date is a proxy for session; two unrelated shoots on one day share a bucket.
- Dates come from filenames, not EXIF. If Roboflow renamed anything the timeline inherits that error.
- The `<untimestamped:counter>` bucket is one bucket covering many real sessions, so a class confined to it is confined to *something*, but the granularity is unknown.
- Instance counts are annotation rows. Missing or wrong annotations propagate directly; the notebook's own author flags relabelling issues in this dataset.
- `rarity` and `session_confined` are not exclusive causes. A class can be both rare and confined; the verdict reports only whether a non-train-only date exists for it.

