# FLAIRE — Thesis Defense Speech Script

**How to use:** Spoken remarks for the 16-slide deck. Read aloud, not memorized — keep the numbers exact. Section estimates sum to roughly 14 minutes 15 seconds; guidance for 15- and 10-minute deliveries is appended.

---

## [Slide 1] — Title & Overview (≈0:55)

Good morning, honored members of the panel. Our study is titled FLAIRE — Flood Level AI Risk Evaluation. FLAIRE is an offline-first flood early-warning prototype built for Barangay Elvita in Narra, Palawan — a riverbank community that experiences seasonal flooding and that, until now, has had no flood warning system tailored to the barangay itself.

In one sentence: we designed, developed, and initially evaluated a solar-powered sensor node that measures river level and rainfall, sends those readings by LoRa radio to a Raspberry Pi 5, and runs a hybrid artificial-intelligence pipeline — a Random Forest model feeding a twenty-rule fuzzy-logic classifier — that turns the live hydrology and cached forecasts into one of four risk levels: Receding, Alert, Alarm, or Critical, displayed on a local dashboard with SMS alerts at the two highest levels. The full build cost about twenty-seven thousand nine hundred twenty pesos. Let me walk you through the journey.

## [Slide 2] — Background of the Study (≈1:05)

*(slide intentionally blank — background content/figure to be inserted; deliver this section from notes.)*

Let me begin in Barangay Elvita. It sits beside a river that floods seasonally, and its flood risk is compounded by the tide. When I say the warning gaps are specific, I mean two things. First, the warnings that do arrive today are municipality-wide advisories — they do not say whether this particular barangay is affected. Second, connectivity drops exactly when warnings matter most: rural network coverage fails precisely during the heavy weather when a community most needs to be told.

Existing flood early-warning system designs transmit sensor data to centralized servers accessed through web platforms — and that chain degrades exactly during the network outages that are common in rural areas during typhoons. What the barangay needs is something that keeps working when the internet does not: local sensing, local classification, local display — with the community's own disaster committee making the final call. That is the design brief FLAIRE answers.

## [Slide 3] — Statement of the Problem (≈0:50)

That is the general problem the study addresses — and it states that problem specifically, in the five questions on screen. First, what are the key problems and limitations in the barangay's current flood-warning practices and data use, and how can an offline-first, AI-based early-warning system address them? Second, how should that system be designed and developed, integrating its four components — cached forecasts, the LoRa-to-Pi sensor link, the hybrid Random Forest plus fuzzy pipeline, and the LAN dashboard with SMS alerts? Third, how consistently does the Random Forest reproduce the rule-derived flood-propensity categories on a held-out test set? Fourth, how does the prototype perform in a limited field deployment — sensor capture, logging, and data quality? Fifth, how acceptable is it to the BDRRMC focal persons, measured through a Technology Acceptance Model survey? Answering these questions is exactly why this study matters — which brings me to its significance.

## [Slide 4] — Significance of the Study (≈0:50)

Who benefits from this study, and how? The BDRRMC of Barangay Elvita does first: an offline-first, AI-enhanced early-warning system that classifies flood risk from real-time sensor data and cached forecasts, supporting decision-making, preemptive evacuation planning, and resource allocation even during internet or power interruptions. Barangay officials and residents benefit next, through timely SMS notifications and dashboard-based monitoring that improve community preparedness in a flood-prone, low-connectivity setting.

Academically, the study contributes a documented, reproducible implementation of an offline-first hybrid Random Forest and fuzzy-logic flood-risk classifier for a rural Philippine barangay, with an honest account of its limitations. At a policy level, it supports the feasibility of barangay-scale, low-cost, power-resilient monitoring for flood-prone communities across the Philippines.

## [Slide 5] — Scope and Delimitation (≈0:50)

Delimitation frames what the study does and does not cover. It is limited to the design, development, and pilot deployment of FLAIRE in Barangay Elvita, Narra, Palawan — one vulnerable river section chosen for riverine flooding. Coastal flooding, upstream flash floods, and flood risks outside the barangay boundaries are excluded. The data boundaries follow the same logic: PAGASA and NAMRIA historical data, Open-Meteo cached forecasts, and LoRa sensor readings from a single river node, all stored in a local SQLite database; final public alert dissemination remains under BDRRMC authority.

The evaluation is bounded too: because the model's labels derive from the same features it consumes, the study measures consistency with the predefined scoring rule. We frame this work deliberately as a decision-support and feasibility study — and I state the boundary plainly: this study does not claim validated flood prediction.

## [Slide 6] — ERD (≈0:50)

The entity-relationship diagram on screen shows FLAIRE's data model: one SQLite database on the Raspberry Pi, with eleven entities in six functional domains. Raw one-minute readings land in sensor_data, whose rain tips are aggregated into rainfall_hourly and rainfall_daily — the windows the model's multi-day features are computed from. tidal_data and weather_data cache the Open-Meteo weather and tide forecasts so the pipeline runs offline within the cache window. The model's output lives in predictions — one row per event covering both the twenty-four-hour and forty-eight-hour horizons, with the Random Forest propensity, the fuzzy inputs, and the rule that fired. alerts and alert_contacts carry the SMS lifecycle from delivery to acknowledgement, while users and audit_log provide authentication and an accountability trail, and system_status tracks component health — with relationships maintained in application code, keeping the schema simple and migration-friendly on SQLite.

## [Slide 7] — System Flowchart: Node (≈0:30)

The flowchart's first segment is the field node. Out on a solar-powered pole by the river, an ultrasonic sensor measures the water distance and a tipping-bucket gauge counts rainfall tips, sampled every minute. Those two numbers travel over the LoRa radio — an RFM95W at nine hundred fifteen megahertz — straight to the barangay hall, with no internet connection involved at any point. That is the entire input side: without it, nothing downstream has anything to classify.

## [Slide 8] — System Flowchart: Edge Device (≈0:40)

The middle segment is the edge device — the Raspberry Pi 5 at the barangay hall. Its LoRa receiver ingests each minute's packet, while a weather-and-tide fetcher caches the seven-day Open-Meteo forecast every six hours whenever internet is available. Both streams persist together in the SQLite database. From those stored inputs, the AI pipeline runs the Random Forest on its eight features and then the twenty fuzzy rules, computing the risk classification for the twenty-four-hour and forty-eight-hour horizons and writing each prediction back to the database. From there, the SMS handler stands ready — it fires only at Alarm and Critical.

## [Slide 9] — System Flowchart: Dashboard (≈0:35)

The last segment is what the barangay actually sees. A FastAPI web server serves a dashboard over the local network — no cloud in the loop — with status cards, charts, and alert history for the BDRRMC. The committee reviews the risk level, confirms every public alert, and the confirmed alerts fan out by SMS to the configured contacts. That is one full cycle, end to end — and as we saw, every piece of it runs without the internet. Which raises the question of what that capability costs — so let me turn to cost and benefits.

## [Slide 10] — Cost and Benefits (≈1:40)

The hardware is deliberately affordable. The bill of materials comes to approximately twenty-seven thousand nine hundred twenty pesos, in three groups. The edge station at the barangay hall is nineteen thousand fifty pesos: the Raspberry Pi 5 two-gigabyte board, at six thousand five hundred pesos, is the main computer, alongside its LoRa transceiver and antenna, a sixty-watt solar panel with controller and lithium-iron-phosphate battery pack, and the A-seven-six-zero-eight-e SMS modem with a year of load for alerts to barangay officials' phones. The river node is seven thousand seventy pesos: its own RFM95 LoRa radio and antenna, a waterproof ultrasonic distance sensor, a small solar panel with charger and battery, a reed switch and magnets for the rain gauge, and its enclosure, PVC pipe, and housing materials. General materials — breadboard, wiring, marine plywood, and miscellaneous electrical components — come to eighteen hundred pesos.

I want to emphasize the cost point because it is a feasibility argument: at this price point, a single barangay budget can adopt the entire architecture. And because it is modular and internet-independent, the same design can be reproduced by other flood-prone communities.

Beyond the price tag, the benefits are technical, operational, and community-wide: continuous water-level and rainfall monitoring without requiring constant internet connectivity; operational support for BDRRMC personnel through continuous hydrological information and AI-based risk classification; and community-level situational awareness and earlier preparedness — reducing dependence on visual water-level observation and external advisories — while final alert dissemination remains under the committee's authority. That closes the design story and returns to the five research questions you saw — first, what the barangay's current practice actually was.

## [Slide 11] — Results: Q1, Current Practices (≈0:40)

First question: what are the problems in the barangay's current flood-warning practices? The BDRRMC focal persons reported that monitoring today relies on a manual rain gauge, visual observation of the river, and a tide calendar, supplemented only by MDRRMO advisories that apply to the entire municipality. That scope is a major limitation — an alert may indicate flooding in parts of Narra without telling Elvita's officials whether their own barangay requires action. Network and power interruptions can further limit communication exactly when warnings matter. What is missing is any continuous, automated, barangay-specific water-level and rainfall record — the gap an offline system could help fill — and it is why the system you have just seen was built.

## [Slide 12] — Results: Q2, System Design and Development (≈0:50)

Second question: how was the system designed and developed? FLAIRE was built as the offline-first answer to that gap, integrating all four components the study specified: cached weather-and-tide forecast data, stored locally for connectivity gaps; the LoRa-based sensor node transmitting water-level and rainfall readings from the river; the Random Forest flood-propensity model — trained on one thousand eight hundred twenty-six daily records from 2020 through 2024 — feeding the twenty-rule fuzzy-logic classifier that combines model output with the live water level and rainfall into Receding, Alert, Alarm, or Critical; and a LAN dashboard with SMS alerting, where the BDRRMC retains final authority over every public release. Every promised component was built, and it runs on the edge device without the internet. Has the heart of it — the model — been checked? That is question three.

## [Slide 13] — Results: Q3, Random Forest Consistency (≈0:50)

Third question: how consistently does the Random Forest reproduce the rule-derived flood-propensity categories? On the eighty-twenty split — one thousand four hundred sixty training records and three hundred sixty-six held-out test records — the model scored ninety-four point two six percent test accuracy, with a macro F1 of zero point nine three three and a weighted F1 of zero point nine four three; the High-propensity class scored ninety-one point six percent F1, and feature importance is dominated by accumulated rainfall — R7, R3, and R1 — which is hydrologically sensible. Now the most important sentence in this presentation: ninety-four point two six percent is agreement with the rule-derived target — the training labels were produced by our own scoring rule over the same eight features — so this figure measures how reliably the model reproduces that rule, not flood-prediction skill. The thesis states this in the abstract and the conclusions, and I am stating it to you. And a consistency check is only as strong as its external probe — which brings us to the field.

## [Slide 14] — Results: Q4, Field Deployment (≈0:50)

Fourth question: how did the prototype perform in the field? We first probed the model externally against the four documented flood events of 2020 through 2025: two classified as High — the two with the strongest accumulated-rainfall signals — and two as Medium, matching our own rule on all four. We report that as diagnostic, not reassuring: the model mirrors the rule rather than encoding flood occurrence — a preliminary case check, not a validation. Then the limited field deployment, installed beside the river in October 2026: the recorded dataset spans roughly twenty-one point five hours — thirteen thousand five hundred sixty-eight records — because the battery depleted sooner than planned. Throughout, the river stayed at low water, the level remained Receding, and no alerts fired — correctly, since no alert condition occurred. Some anomalous sensor readings were flagged for quality review, and rainfall entries await validation; what the run validated is the sensor-and-logging pipeline under real conditions — and we claim exactly that. Which leaves the last question: do the operators accept it?

## [Slide 15] — Results: Q5, Acceptability (≈0:40)

Fifth question: how acceptable is the system to its operators? We administered a Technology Acceptance Model survey to the two BDRRMC focal persons — twenty-four five-point Likert items across six dimensions. Functionality, perceived reliability, contribution to preparedness, attitude, and intention to use each rated a perfect five point zero; usability rated four point seven five. I must flag the small sample directly: with two respondents, these are preliminary ratings and should not be generalized — but they are an honest, encouraging signal from the system's intended operators. Those five answers close the results — so let me pull the study together.

## [Slide 16] — Summary, Conclusion and Recommendation (≈1:40)

To close: the summary, conclusions, and recommendations. Three findings anchor this study. First, the barangay's current practice is manual — municipality-wide advisories and word of mouth — which establishes the need for localized, internet-independent monitoring. Second, the evaluated prototype achieved ninety-four point two six percent held-out agreement with its own rule-derived labels, and, in the field, logged twenty-one point five hours and thirteen thousand five hundred sixty-eight records — validating the sensor-and-logging pipeline under real conditions. Third, the two BDRRMC focal persons rated the system a perfect five point zero on five TAM dimensions and four point seven five on usability — encouraging, and explicitly not generalizable.

Our conclusions follow: FLAIRE is technically feasible as an offline-first, edge-based decision-support tool; its predictive skill is not yet demonstrated — the model reproduces its own rule, and we state that plainly; and the design keeps people in charge, with the BDRRMC confirming every public alert and the AI layer architecturally replaceable once independent labels exist.

Which leads to the recommendations: build independent flood-event labels; validate chronologically once they exist; harden the power system and repeat a full-season deployment; validate the ultrasonic sensor and rain gauge against reference instruments; widen the acceptability survey beyond the two focal persons; and pursue multi-node expansion along the river. Those are our recommendations. Thank you — we now welcome your questions.

---

## Appendix — Timing Guide

- **15 minutes (target):** Deliver all 16 sections as written, at a natural 145–150 words per minute. The section estimates sum to roughly 14 minutes 15 seconds — a 15-minute slot, tight but workable, with the figure-pointing moments in Sections 6, 7, 8, and 9. To fill the full fifteen with depth, add three expansions without inventing facts: Section 13 — walk one illustrative fuzzy rule aloud, name the per-class numbers (Low 97 F1, Medium 91, High 92), and note the confusion matrix shows errors never jump across two classes. Section 5 — quote the delimitations one by one. Section 4 — walk each beneficiary group through its specific payoff.
- **10 minutes (compressed):** Keep Sections 1, 2, and 13 nearly intact — the overview, the background, and the results with the verbatim caveat are load-bearing. Collapse Sections 11–15 to the Q3 metrics plus one sentence each; collapse Sections 7, 8, and 9 to one sentence each and point to each figure; reduce Section 3 to the general problem and a quick pass over the five questions; Sections 4, 5, and 6 to their core sentences; Section 10 to the three-group total and one benefit; and Section 16 to the conclusions plus the recommendations list. Saves roughly 4 minutes 15 seconds.
- **Hard rules at any speed:** never say "predicts floods," never claim a measured lead time, never say SMS was field-exercised, and always read the caveat sentence in Section 13 verbatim.
