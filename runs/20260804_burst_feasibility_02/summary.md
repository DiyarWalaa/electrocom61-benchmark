# Can the rescued classes be moved as whole bursts?

Run directory: `20260804_burst_feasibility_02`

Never-evaluated classes: **15**. Train-only groups: 20240219, 20240220, <untimestamped:counter>.

A class can be rescued cleanly only if it appears in **two or more distinct groups each carrying >= 5 instances** -- one to send to valid, a different one to test.

## Verdict counts by setting

| regime | setting | absent from regime | single group (unavoidable) | several groups but < 2 qualifying | has alternatives |
|---|---|---|---|---|---|
| timestamp | tau=3s | 2 | 0 | 12 | 1 |
| timestamp | tau=5s | 2 | 0 | 5 | 8 |
| timestamp | tau=10s | 2 | 0 | 1 | 12 |
| timestamp | tau=30s | 2 | 0 | 0 | 13 |
| timestamp | tau=60s | 2 | 0 | 0 | 13 |
| scene-component | eps=0.01 | 0 | 0 | 4 | 0 |
| scene-component | eps=0.02 | 0 | 0 | 4 | 0 |
| scene-component | eps=0.05 | 0 | 0 | 2 | 2 |

## Combined answer (tau=10s, epsilon=0.05)

**14 of 15** never-evaluated classes can be rescued by moving whole groups.

| class | timestamped regime | scene-component regime | rescuable cleanly? | via |
|---|---|---|---|---|
| 9-Volt-Battery | has_alternatives | absent_from_regime | YES | timestamped bursts |
| Bluetooth-Module | has_alternatives | absent_from_regime | YES | timestamped bursts |
| Buzzer | has_alternatives | absent_from_regime | YES | timestamped bursts |
| Gas-Sensor | has_alternatives | insufficient | YES | timestamped bursts |
| High-Voltage-Ceramic-Capacitor | has_alternatives | absent_from_regime | YES | timestamped bursts |
| Inductor | has_alternatives | absent_from_regime | YES | timestamped bursts |
| LCD-Display | has_alternatives | absent_from_regime | YES | timestamped bursts |
| LDR-Sensor | has_alternatives | absent_from_regime | YES | timestamped bursts |
| LED-Light | absent_from_regime | has_alternatives | YES | scene components |
| MLC-Capacitor | has_alternatives | absent_from_regime | YES | timestamped bursts |
| Motor-Driver | has_alternatives | absent_from_regime | YES | timestamped bursts |
| OLED-Display | absent_from_regime | has_alternatives | YES | scene components |
| Push-Switch | has_alternatives | absent_from_regime | YES | timestamped bursts |
| RFID-Scanner | insufficient | absent_from_regime | **NO** | - |
| Sonar-Sensor | has_alternatives | insufficient | YES | timestamped bursts |

## Per class, timestamped regime

**tau = 3s**

| class | groups w/ class | groups w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| 9-Volt-Battery | 152 | 0 | 0 | 0 | insufficient |
| Bluetooth-Module | 173 | 0 | 0 | 0 | insufficient |
| Buzzer | 198 | 0 | 0 | 0 | insufficient |
| Gas-Sensor | 66 | 0 | 0 | 0 | insufficient |
| High-Voltage-Ceramic-Capacitor | 194 | 0 | 0 | 0 | insufficient |
| Inductor | 177 | 0 | 0 | 0 | insufficient |
| LCD-Display | 168 | 0 | 0 | 0 | insufficient |
| LDR-Sensor | 78 | 1 | 2 | 2 | insufficient |
| LED-Light | 0 | 0 | 0 | 0 | absent_from_regime |
| MLC-Capacitor | 80 | 19 | 1 | 2 | has_alternatives |
| Motor-Driver | 167 | 0 | 0 | 0 | insufficient |
| OLED-Display | 0 | 0 | 0 | 0 | absent_from_regime |
| Push-Switch | 169 | 0 | 0 | 0 | insufficient |
| RFID-Scanner | 146 | 0 | 0 | 0 | insufficient |
| Sonar-Sensor | 70 | 0 | 0 | 0 | insufficient |

**tau = 5s**

| class | groups w/ class | groups w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| 9-Volt-Battery | 119 | 0 | 0 | 0 | insufficient |
| Bluetooth-Module | 148 | 1 | 3 | 3 | insufficient |
| Buzzer | 161 | 4 | 3 | 5 | has_alternatives |
| Gas-Sensor | 51 | 3 | 3 | 3 | has_alternatives |
| High-Voltage-Ceramic-Capacitor | 166 | 2 | 3 | 3 | has_alternatives |
| Inductor | 146 | 3 | 3 | 5 | has_alternatives |
| LCD-Display | 137 | 1 | 5 | 5 | insufficient |
| LDR-Sensor | 60 | 8 | 2 | 4 | has_alternatives |
| LED-Light | 0 | 0 | 0 | 0 | absent_from_regime |
| MLC-Capacitor | 62 | 25 | 1 | 4 | has_alternatives |
| Motor-Driver | 130 | 0 | 0 | 0 | insufficient |
| OLED-Display | 0 | 0 | 0 | 0 | absent_from_regime |
| Push-Switch | 138 | 5 | 2 | 4 | has_alternatives |
| RFID-Scanner | 126 | 0 | 0 | 0 | insufficient |
| Sonar-Sensor | 55 | 5 | 2 | 3 | has_alternatives |

**tau = 10s**

| class | groups w/ class | groups w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| 9-Volt-Battery | 78 | 4 | 4 | 10 | has_alternatives |
| Bluetooth-Module | 91 | 12 | 3 | 6 | has_alternatives |
| Buzzer | 95 | 12 | 3 | 10 | has_alternatives |
| Gas-Sensor | 38 | 6 | 3 | 4 | has_alternatives |
| High-Voltage-Ceramic-Capacitor | 105 | 10 | 3 | 6 | has_alternatives |
| Inductor | 90 | 11 | 3 | 10 | has_alternatives |
| LCD-Display | 89 | 3 | 5 | 10 | has_alternatives |
| LDR-Sensor | 46 | 12 | 2 | 4 | has_alternatives |
| LED-Light | 0 | 0 | 0 | 0 | absent_from_regime |
| MLC-Capacitor | 48 | 22 | 1 | 4 | has_alternatives |
| Motor-Driver | 89 | 5 | 3 | 10 | has_alternatives |
| OLED-Display | 0 | 0 | 0 | 0 | absent_from_regime |
| Push-Switch | 85 | 20 | 3 | 10 | has_alternatives |
| RFID-Scanner | 80 | 1 | 6 | 6 | insufficient |
| Sonar-Sensor | 41 | 7 | 2 | 4 | has_alternatives |

**tau = 30s**

| class | groups w/ class | groups w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| 9-Volt-Battery | 24 | 11 | 5 | 33 | has_alternatives |
| Bluetooth-Module | 43 | 19 | 3 | 20 | has_alternatives |
| Buzzer | 21 | 16 | 3 | 33 | has_alternatives |
| Gas-Sensor | 25 | 7 | 3 | 9 | has_alternatives |
| High-Voltage-Ceramic-Capacitor | 44 | 19 | 3 | 20 | has_alternatives |
| Inductor | 23 | 15 | 3 | 33 | has_alternatives |
| LCD-Display | 25 | 11 | 5 | 33 | has_alternatives |
| LDR-Sensor | 27 | 14 | 2 | 9 | has_alternatives |
| LED-Light | 0 | 0 | 0 | 0 | absent_from_regime |
| MLC-Capacitor | 27 | 23 | 1 | 9 | has_alternatives |
| Motor-Driver | 35 | 11 | 7 | 33 | has_alternatives |
| OLED-Display | 0 | 0 | 0 | 0 | absent_from_regime |
| Push-Switch | 23 | 18 | 3 | 33 | has_alternatives |
| RFID-Scanner | 39 | 14 | 5 | 20 | has_alternatives |
| Sonar-Sensor | 26 | 10 | 2 | 9 | has_alternatives |

**tau = 60s**

| class | groups w/ class | groups w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| 9-Volt-Battery | 9 | 7 | 10 | 50 | has_alternatives |
| Bluetooth-Module | 14 | 11 | 3 | 64 | has_alternatives |
| Buzzer | 9 | 9 | 6 | 50 | has_alternatives |
| Gas-Sensor | 13 | 8 | 3 | 19 | has_alternatives |
| High-Voltage-Ceramic-Capacitor | 14 | 11 | 3 | 64 | has_alternatives |
| Inductor | 9 | 9 | 6 | 50 | has_alternatives |
| LCD-Display | 9 | 7 | 10 | 50 | has_alternatives |
| LDR-Sensor | 15 | 11 | 2 | 19 | has_alternatives |
| LED-Light | 0 | 0 | 0 | 0 | absent_from_regime |
| MLC-Capacitor | 15 | 14 | 2 | 19 | has_alternatives |
| Motor-Driver | 23 | 11 | 7 | 50 | has_alternatives |
| OLED-Display | 0 | 0 | 0 | 0 | absent_from_regime |
| Push-Switch | 9 | 9 | 6 | 50 | has_alternatives |
| RFID-Scanner | 13 | 9 | 6 | 64 | has_alternatives |
| Sonar-Sensor | 13 | 8 | 3 | 19 | has_alternatives |

## Per class, untimestamped regime (scene components)

Bursts are undefined for these images. Components group by appearance, not time, and are a weaker instrument.

**epsilon = 0.01**

| class | components w/ class | components w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| Gas-Sensor | 111 | 0 | 0 | 0 | insufficient |
| LED-Light | 183 | 0 | 0 | 0 | insufficient |
| OLED-Display | 188 | 0 | 0 | 0 | insufficient |
| Sonar-Sensor | 117 | 0 | 0 | 0 | insufficient |

**epsilon = 0.02**

| class | components w/ class | components w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| Gas-Sensor | 109 | 0 | 0 | 0 | insufficient |
| LED-Light | 179 | 0 | 0 | 0 | insufficient |
| OLED-Display | 183 | 0 | 0 | 0 | insufficient |
| Sonar-Sensor | 113 | 0 | 0 | 0 | insufficient |

**epsilon = 0.05**

| class | components w/ class | components w/ >=5 | smallest qualifying (imgs) | largest (imgs) | verdict |
|---|---|---|---|---|---|
| Gas-Sensor | 87 | 0 | 0 | 0 | insufficient |
| LED-Light | 144 | 4 | 3 | 5 | has_alternatives |
| OLED-Display | 146 | 3 | 3 | 5 | has_alternatives |
| Sonar-Sensor | 91 | 0 | 0 | 0 | insufficient |

## What could make this misleading

- Two distinct bursts can still be near-duplicates of each other. Separate bursts are a NECESSARY condition for a clean rescue, not a sufficient one; the allocator would still have to check geometry.
- Capture date is a proxy for session and tau is a proxy for burst. A pause longer than tau inside one continuous shoot splits it into two groups that are not really alternatives.
- Scene components are appearance-based. Under-merging invents alternatives that are duplicates; over-merging hides real ones. The epsilon sweep is there so this is visible.
- Group SIZE is a hard budget the allocator must respect: test holds only 205 images, so a large burst may be unusable even when it qualifies on instance count.

