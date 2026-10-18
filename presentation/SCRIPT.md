# FLAIRE — Thesis Defense Speech Script

**How to use:** Spoken remarks for the 14-slide deck. Read aloud, not memorized — keep the numbers exact. Section estimates sum to roughly 13 minutes 50 seconds; compression guidance for 12 and 10 minutes is appended.

---

## [Slide 1] — Title & Overview (≈0:55)

Good morning, honored members of the panel. Our study is titled FLAIRE — Flood Level AI Risk Evaluation. FLAIRE is an offline-first flood early-warning prototype built for Barangay Elvita in Narra, Palawan — a riverbank community that experiences seasonal flooding and that, until now, has had no flood warning system tailored to the barangay itself.

In one sentence: we designed, developed, and initially evaluated a solar-powered sensor node that measures river level and rainfall, sends those readings by LoRa radio to a Raspberry Pi 5, and runs a hybrid artificial-intelligence pipeline — a Random Forest model feeding a twenty-rule fuzzy-logic classifier — that turns the live hydrology and cached forecasts into one of four risk levels: Receding, Alert, Alarm, or Critical, displayed on a local dashboard with SMS alerts at the two highest levels. The full build cost about twenty-seven thousand nine hundred twenty pesos. Let me walk you through the journey, starting with the problem itself.

## [Slide 2] — Standard Operating Procedure (≈0:50)

We start with the standard operating procedure — how the barangay actually runs FLAIRE day to day. In normal operation, the river node beams water-level and rainfall readings over LoRa radio to the Raspberry Pi 5 at the barangay hall; classification, storage, and the dashboard all run locally on that Pi, so the system keeps working when the internet is down. A duty monitor signs in on the local network and checks the live link, system status, sensor health, and the twenty-four and forty-eight-hour risk badges. SMS fires only at the two highest levels — Alarm and Critical — and the BDRRMC confirms every public alert; the system never acts autonomously.

Maintenance is simple and scheduled: inspect cabling and enclosures, monitor battery and charging on the dashboard's status cards, validate the rain gauge against its zero-point-two-millimeters-per-tip calibration, and keep the station's clock synchronized so every timestamp stays trustworthy.

## [Slide 3] — Problem & Setting (≈1:00)

Let me begin in Barangay Elvita. It sits beside a river that floods seasonally, and its flood risk is compounded by the tide. When I say the warning gaps are specific, I mean two things. First, the warnings that do arrive today are municipality-wide advisories — they do not say whether this particular barangay is affected. Second, connectivity drops exactly when warnings matter most: rural network coverage fails precisely during the heavy weather when a community most needs to be told.

Existing flood early-warning system designs transmit sensor data to centralized servers accessed through web platforms — and that chain degrades exactly during the network outages that are common in rural areas during typhoons. What the barangay needs is something that keeps working when the internet does not: local sensing, local classification, local display — with the community's own disaster committee making the final call. That is the design brief FLAIRE answers.

## [Slide 4] — Objectives & Scope (≈0:55)

We frame this work deliberately as a decision-support and feasibility study — the barangay disaster committee confirms every public alert; the system never acts autonomously.

Our five research questions were: the problems in the barangay's current warning practice; the design of the AI-based system with its components; how consistently the Random Forest model reproduces the rule-derived flood-risk categories; how the system performs in a real field deployment; and how acceptable it is to the barangay's disaster-risk focal persons.

I want to state the boundary plainly, because it governs everything you will hear: this study does not claim validated flood prediction. It claims a working, evaluated prototype — and we will report the results, including the candid ones, with exactly that scope.

## [Slide 5] — System Architecture (≈1:00)

Here is the architecture. A solar-powered sensor node by the river measures water distance and rainfall tips, and transmits them over LoRa radio — low-power, kilometers-range, no internet required — to the barangay hall, where a Raspberry Pi 5 receives the stream every minute.

On that single device, three things happen locally. The readings are stored in an SQLite database. The AI pipeline runs: the Random Forest estimates a meteorological flood propensity, and the fuzzy-logic classifier combines that propensity with the live water level, its rate of rise, forecast rainfall, and the tide to produce the risk level. And the dashboard serves the result — a FastAPI web application over the local network, so the barangay can see it without any internet connection. Internet is used for exactly one purpose: refreshing cached weather and tide forecasts from Open-Meteo. When the internet is down, nothing changes — classification, storage, dashboard, and SMS alerting all run on the local device. That is what offline-first means, and it is the architectural core of this thesis.

## [Slide 6] — Hardware & Cost (≈1:00)

The hardware is deliberately affordable. The bill of materials comes to approximately twenty-seven thousand nine hundred twenty pesos, in three groups. The edge station at the barangay hall is nineteen thousand fifty pesos: the Raspberry Pi 5 two-gigabyte board, at six thousand five hundred pesos, is the main computer, alongside its LoRa transceiver and antenna, a sixty-watt solar panel with controller and lithium-iron-phosphate battery pack, and the A-seven-six-zero-eight-e SMS modem with a year of load for alerts to barangay officials' phones. The river node is seven thousand seventy pesos: its own RFM95 LoRa radio and antenna, a waterproof ultrasonic distance sensor, a small solar panel with charger and battery, a reed switch and magnets for the rain gauge, and its enclosure, PVC pipe, and housing materials. General materials — breadboard, wiring, marine plywood, and miscellaneous electrical components — come to eighteen hundred pesos.

I want to emphasize the cost point because it is a feasibility argument: at this price point, a single barangay budget can adopt the entire architecture. And because it is modular and internet-independent, the same design can be reproduced by other flood-prone communities.

## [Slide 7] — Data Pipeline (≈0:55)

The data pipeline runs at one-minute resolution. The LoRa sensor reports a distance in millimeters and a tip count. Distance converts to a water level by a simple subtraction — two point five meters minus the measured distance, because the sensor is mounted above the waterline. Rainfall is tips times zero point two millimeters, which is the standard resolution of this class of tipping-bucket gauge; daily totals are aggregated into a rainfall history, from which the model's multi-day rainfall features are computed.

Alongside the sensor stream, the system fetches a seven-day weather and tide forecast from Open-Meteo — precipitation, temperature maximum and minimum, and marine tide levels — every six hours, cached locally so that no prediction ever waits on connectivity. The prediction pipeline then computes a rate of rise from the last five minutes of level data, builds the model features for two horizons — a twenty-four-hour and a forty-eight-hour forecast — runs the Random Forest and the fuzzy classifier on both, and stores one prediction row covering the two horizons.

## [Slide 8] — Methodology (≈1:25)

Now the methodology — this is the heart of the study. The Random Forest was trained on one thousand eight hundred twenty-six daily records covering 2020 through 2024, sourced from PAGASA rainfall and temperature data and NAMRIA tide data. Its eight input features are: R1, R3, and R7 — the rainfall totals for the previous one, three, and seven days — the count of consecutive rainy days, daily maximum and minimum temperature, and the maximum and minimum tide level in the seven-day forecast window. Its output is a flood-propensity class — Low, Medium, or High.

The Random Forest does not decide the risk level by itself. It feeds a twenty-rule fuzzy-logic classifier — fifteen core rules plus five gap-fill rules — whose five inputs are the water level, the rate of rise, forecast rainfall, the tide, and the model's propensity. The fuzzy layer is deliberately explicit and readable, so the barangay can audit every decision path; the machine-learning layer is deliberately replaceable. Together they produce the final output: four risk levels — Receding, Alert, Alarm, Critical — computed for two horizons, twenty-four and forty-eight hours, shown side by side on the dashboard.

Our evaluation strategy has five pieces: the functional verification of the fuzzy layer, the model training on a stratified eighty-twenty split, a check against four documented flood events from the barangay records, a real field deployment, and the acceptability survey. Each has results — and each has an honest caveat, which I will name as we go.

## [Slide 9] — Model Results (≈1:20)

On the eighty-twenty split — one thousand four hundred sixty training records and three hundred sixty-six held-out test records — the model scored ninety-four point two six percent test accuracy, with a macro F1 of zero point nine three three and a weighted F1 of zero point nine four three. Per class, the High-propensity class scored ninety-one point six percent F1. Feature importance is dominated by accumulated rainfall: R7 at zero point four zero, R3 at zero point two four, and R1 at zero point one one — the weekly rainfall story carries the signal, which is hydrologically sensible.

Now the most important sentence in this presentation: ninety-four point two six percent is agreement with the rule-derived target — the training labels were produced by our own scoring rule over the same eight features — so this figure measures how reliably the model reproduces that rule, not flood-prediction skill. The thesis states this in the abstract and the conclusions, and I am stating it to you. We knew our check against four documented flood events would probe exactly this — let me show what it found.

## [Slide 10] — Deployment Results (≈1:00)

First, the four-event retrospective check. Against barangay flood records for 2021 to 2023, the model classified two of the four documented floods as High — the two with the strongest accumulated-rainfall signals — and the other two as Medium. On all four events, the model's verdict matched our own rule. We report this as diagnostic, not reassuring: it shows the model mirrors the rule rather than encoding flood occurrence, and that our feature set represents rainfall more than floods. It is a preliminary case check, not a validation.

Second, the field deployment. We installed the prototype beside the river in Elvita in October 2026. The recorded dataset spans roughly twenty-one point five hours and thirteen thousand five hundred sixty-eight records — the battery depleted sooner than planned. Throughout that run, the river stayed at low water, the level remained Receding, and no alerts fired — correctly, because no alert condition occurred. The SMS capability works and was enabled on the deployed unit; it triggers only at Alarm and Critical, which the deployment never reached. What the run validated is the sensor-and-logging pipeline under real field conditions — and we claim exactly that.

## [Slide 11] — TAM Survey (≈0:45)

Now, acceptability. We administered a Technology Acceptance Model survey to the two BDRRMC focal persons — the people who would actually operate the system. The instrument has six dimensions — functionality, usability, perceived reliability, contribution to preparedness, attitude, and intention to use — with twenty-four five-point Likert items. Five dimensions rated a perfect five point zero; usability rated four point seven five.

I must flag the small sample directly: with two respondents, these are preliminary ratings and should not be generalized to all barangay officials or residents. They are initial evidence that the instrument and the interface work — and an honest, encouraging signal from the system's intended operators.

## [Slide 12] — Summary of Findings (≈1:00)

Let me pull the study together in six findings. First, the barangay's current practice is manual: warnings are municipality-wide advisories and word of mouth, and connectivity drops exactly when they matter most. Second, documenting those practices establishes the need for localized, internet-independent monitoring — the gap FLAIRE is built to fill. Third, the Random Forest scored ninety-four point two six percent on held-out data — agreement, as the caveat states, with our own rule-derived labels, not flood-prediction skill. Fourth, two of the four documented flood events matched the rule's High classification — a diagnostic case check, not a validation. Fifth, the field deployment recorded twenty-one point five hours — thirteen thousand five hundred sixty-eight records — while the river stayed Receding and the sensor-and-logging pipeline was validated under real conditions. Sixth, the two BDRRMC focal persons — an n of two — rated five TAM dimensions a perfect five point zero and usability four point seven five: encouraging, and explicitly not generalizable.

## [Slide 13] — Conclusions (≈0:55)

Our conclusions are three. First, feasibility is established: FLAIRE is a working offline-first, edge-based decision-support tool — solar sensing, LoRa transfer, local classification, a LAN dashboard, SMS alerting — demonstrated in the field and affordable at barangay scale. Second, predictive skill is not yet demonstrated: the model reproduces its own rule, so the accuracy figure measures rule consistency, and we state that plainly rather than claim prediction. Third, the design keeps people in charge: the BDRRMC confirms every public alert, the transparent fuzzy rules remain auditable, and the AI layer is architecturally replaceable — once independent flood-event labels exist, the model can be retrained without disturbing the rules the barangay already understands.

## [Slide 14] — Recommendations (≈0:50)

Finally, our recommendations. First, and most important: build independent flood-event labels — from barangay logs and PAGASA records — so evaluation no longer leans on the model's own rule. Second, once those labels exist, validate chronologically: train on earlier years and test on later floods. Third, harden the power system and repeat the deployment across a full flood season, so Alert, Alarm, and Critical are exercised in real conditions. Fourth, validate the ultrasonic sensor against a staff gauge and the rain gauge against a reference instrument, also addressing the anomalous readings we saw. Fifth, widen the acceptability survey beyond the two focal persons to residents as well. Sixth, pursue multi-node expansion — additional LoRa nodes along the river to cover the whole waterway. Those are our recommendations. Thank you — we now welcome your questions.

---

## Appendix — Timing Guide

- **15 minutes (target):** Deliver all 14 sections as written, at a natural 145–150 words per minute. The section estimates sum to roughly 13 minutes 50 seconds — a 15-minute slot with room for pauses and transitions. To fill the full fifteen with depth, add three expansions without inventing facts: Section 8 — walk one illustrative fuzzy rule aloud (e.g., very high water level with rapid rise); Section 9 — name the per-class numbers (Low 97 F1, Medium 91, High 92) and note the confusion matrix shows errors never jump across two classes; Section 4 — quote the five research questions one by one.
- **12 minutes (slightly compressed):** Compress Section 8 by skipping the eight-feature enumeration (point to the slide); Section 7 to the two conversion facts and six-hour cache; Section 10's four-event detail to one sentence ("we report it as a preliminary case check showing model-rule agreement"); and Sections 11–13 to two sentences each. Saves roughly 1 minute 50 seconds.
- **10 minutes (compressed):** Keep Sections 1, 3, 5, 9, and 13 nearly intact — overview, problem, architecture, model results with the verbatim caveat, and conclusions are load-bearing. Apply every cut above, plus: reduce Section 2 to the operation paragraph; deliver Section 12's six findings as one clause each; cut Sections 6, 11, and 14 to one or two sentences. Saves roughly 3 minutes 50 seconds.
- **Hard rules at any speed:** never say "predicts floods," never claim a measured lead time, never say SMS was field-exercised, and always read the caveat sentence in Section 9 verbatim.
