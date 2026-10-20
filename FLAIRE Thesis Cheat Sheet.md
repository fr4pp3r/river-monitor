# FLAIRE — Thesis Cheat Sheet & Chapter 2 Theory Guide

**Thesis:** FLAIRE: Offline-First Flood Early Warning System Using LoRa Sensors for Brgy. Elvita, Narra, Palawan
**Full name:** Flood Level AI Risk Evaluation
**Authors:** Betita, Cabotaje, Gabo, Hamad, Unos (5) | **Adviser:** Joel P. Gulane Jr.

---

## PART A — THE NUMBERS (memorize these cold)

| Item | Value |
|---|---|
| Training data | 1,826 daily records, 2020-01-02 to 2024-12-31 (PAGASA met + NAMRIA tide) |
| Split | Stratified 80/20 → 1,460 train / 366 test |
| RF accuracy | **94.26%** (345/366 correct) |
| F1 scores | Low 0.97 · Medium 0.91 · High 0.92 |
| Weighted avg | 0.9433 precision / 0.9426 recall / 0.9426 F1 |
| High class | Recall 0.9524 (60/63) · Precision 0.8824 (8 Medium→High) |
| RF features (8) | R1, R3, R7, rain_days, TMAX, TMIN, TideMax, TideMin |
| Fuzzy rules | 20 total = 15 core + 5 gap-fill |
| Fuzzy inputs (5) | water level (0–3000 mm), rate of rise, forecast rain, tide, RF propensity |
| Fuzzy outputs (4) | Receding, Alert, Alarm, Critical |
| Rule resolution | 768 combos swept, 3,150 grid points; 296 (38.5%) by explicit rule, rest by weighted fallback |
| Deployment | 13,568 LoRa records, ~21.5 hours |
| Deployment levels | median water level 0.122 m, range −0.012 to 2.500 m |
| Deployment anomalies | 67 zero-distance/2.500 m, 124 negative, 5 implausible short |
| Deployment reached | **Receding only** — Alert/Alarm/Critical never exercised |
| Acceptability (n=2) | functionality 5.00 · usability 4.75 · others 5.00 |
| Total cost | **₱23,700** (Pi 5 alone ₱6,500) |
| Flood events | 4 documented: 21/10/2021, 30/03/2022, 27/12/2022, 23/11/2023 → **2 High / 2 Medium** |
| Forecast horizon | Cached Open-Meteo, 7 days, updated every 6 h |

**Fuzzy water-level breakpoints (current code, `src/config.py`):**
Alert < 0.914 m · Alarm 0.914–1.219 m · Critical ≥ 1.219 m · Very High ≥ 1.829 m

---

## PART B — WHAT THE THESIS DOES AND DOES NOT CLAIM

**Claims (safe to say):**
- Built and field-tested an offline-first flood **risk classification and decision-support** system
- RF reproduces its rule-derived labels with 94.26% agreement — **consistency**, not flood-prediction accuracy
- Fuzzy layer is functionally complete: all 768 combos + 3,150 grid points return a defined class, output monotonic in water level and rate of rise
- System is feasible on low-cost edge hardware for a barangay with poor connectivity

**Never say (the thesis denies these):**
- "The model predicts floods" — it was trained on rule-derived labels from the same features (P250, P524, P603)
- "We measured lead time" — explicitly out of scope, future work (P250, P526, P604)
- "We beat a threshold baseline" — comparison not completed, future work (P344, P526, P604)
- "Two sensor nodes" / "monsoon-season campaign" — single node, ~21.5 h (P252)
- "It was tested in a typhoon" — deployment stayed at Receding (P633)

---

## PART C — CHAPTER 2 CONTENTS (theoretical knowledge)

### C1. Theoretical Framework (P276–P295)
The chapter grounds the study in disaster-risk and technology-adoption theory, then describes the system concept.

**Philippine policy backbone:**
- **NDRRMP 2020–2030** (NDRRMP) — national DRRM blueprint; RBMES with 23 outcomes; prior gap was absence of functional, standardized DRRM M&E at all levels
- **KOICA–DOST-PAGASA EWS4 Project** (Nov 2023, US$12.7 M, 2021–2026) — x-band radar, gauges, flow meters, CCTV; goal to increase evacuation lead time
- **Palawan provincial FEWS** — 20 units installed; Brgy. Elvita was the first site (Radyo Natin report)

**Early-warning theory (4 key stages, GSMA):**
1. Risk knowledge → 2. Forecasting & warning → 3. Dissemination & communication → 4. Preparedness & response

**Mobile / multi-channel theory:**
- **ITU review (Gray)** — location-based SMS + cell broadcast; redundancy across sirens, radio, TV, apps, social media; EU mandate; **UN Early Warnings for All (EW4A, Mar 2022)** — universal coverage by 2027
- **Budimir et al. (MHEWS)** — people-centered multi-hazard systems fail when community engagement, localization, and vulnerability dynamics are ignored
- **STREAM-EWS (PIN / SMART / GSMA)** — 55,000+ direct users, 335,000 indirect; 32 weather stations; private-sector + grassroots model
- **DOST-ASTI 2024 Annual Report** — AI/IoT/microelectronics investment (FLASH, SAGAP, DIMER "model store")

**Enabling technology:**
- **Semtech (LoRa / LoRaWAN)** — LPWAN standard; up to 15 km rural / 5 km urban; ~10-year battery life; star topology; up to 10,000 devices per gateway

### C2. Review of Related Studies (P296–P308)
Evidence base for each design choice, split local vs foreign.

| Study | Design | Relevance to FLAIRE |
|---|---|---|
| Cacal, Austria & Taboada (2023) | HEC-HMS rainfall-runoff, Irawan basin, Palawan | Local watershed context, data-scarce basins |
| Kim et al. | DNN + XGBoost/RF classification, Biliran | DNN NRMSE 9.48; XGBoost F1 0.92; AI in PH flood context |
| Macalalad et al. (2021) | Liuxihe PBDHM, Matina River, Davao | Data-poor modeling; remote sensing + hybrid |
| Miyamoto et al. | Co-design + ISSSR, Davao City | Stakeholder-engaged, barangay-scale risk communication |
| Mesias & Bagtasa (2025) | SOM + RF for TC rainfall, PH | RF for PH meteorological prediction; low compute |
| Ahmed | LoRa water-level sensor, drainage | Hardware: ±2 cm, 69.2 µA, 6.5-yr battery |
| Schumacher et al. | CSU-MLP, random forest, US | Research-to-operations ML transition; probabilistic EROs |
| Sehgal, Gurudiwan & Pant | Remote sensing + edge computing | Low-latency real-time warning pipelines |
| Refadah | Systematic ML/AI flood review | Ensemble methods (RF) consistently strong |
| Bibi et al. | SVM/XGBoost/ANN/LSTM/GRU, Kabul River | LSTM R²=0.96, RMSE 140.96 m³/s; multi-day windows |

### C3. Conceptual Framework (P310–P322)
**IPO model** — three inputs, one process, three outputs.

- **Inputs:** ① cached 7-day Open-Meteo weather + tide forecasts (updated ≤6 h) ② real-time LoRa sensor data (ultrasonic water level + rain gauge) ③ historical reference data (PAGASA, NAMRIA, local flood records)
- **Process:** hybrid Fuzzy-AI pipeline on Raspberry Pi 5 → RF estimates flood propensity → 20-rule fuzzy classifier fuses with live water level, rate of rise, forecast rain, tide
- **Outputs:** ① LAN web dashboard ② SMS notifications (Alarm/Critical) ③ logged classifications; **final alert authority stays with BDRRMC**
- **Figure 2.1** — schematic of the IPO framework

### C4. Research Paradigm (P318–P327)
- **Paradigm:** developmental and evaluative research, post-positivist tradition
- **Model:** Input-Process-Output (IPO)
- **Design logic:** independent variables (forecast + sensor inputs, historical data) → processes → dependent outcomes (risk classification, alert delivery, performance measures)
- Ensures RQs, objectives, and evaluation criteria are systematically aligned

---

## PART D — TOP DEFENSE QUESTIONS (say it this way)

**Q: "Your labels came from the same features the model trained on. What did the RF add?"**
> The RF added a reproducible, edge-executable approximation of our scoring rule — 94.26% agreement. It did not add independent predictive skill; we say so explicitly. The AI layer's value is that it runs offline on a Pi, and its usefulness beyond the composite score remains to be shown with independent flood-event labels. *(P250, P603, P606)*

**Q: "Only 2 of 4 floods were High, and both were ones your rule already flags."**
> Correct. The 94.26% reflects agreement with our own rule, not flood prediction. The four-event check shows the rule-derived labels capture accumulated-rainfall signals but do not reliably encode flood occurrence — which is why independent labels and chronological validation are the top recommendations. *(P538, P603, P606)*

**Q: "Did the system ever actually send an SMS?"**
> SMS is implemented and fires at Alarm and Critical, but the deployment never rose above Receding, so no alert fired in the field. The capability is there; the real-event trigger test is future work. *(P249, P604)*

**Q: "38.5% hit an explicit rule — 61.5% is a hand-weighted fallback. Who validated the weights?"**
> The weights are the fuzzy membership centroids, not tuned predictions. We verified functional completeness — all 768 combos and 3,150 grid points return a defined class, output monotonic in water level and rate of rise, no runtime errors. It was not validated against real flood outcomes. *(P480–P482)*

**Q: "Title says January 2026, deployment says October 2026."**
> *(Verify the fix before printing — this is the #1 question and the only one that must be eliminated, not answered.)*

**Q: "What's the cost?"**
> ₱23,700 total. The Pi 5 is ₱6,500 of it. Low enough for a barangay budget; full table in Chapter 4.

---

*Paragraph references (P###) point into the current revised file. Abstract is split across P109–P110 (230 words). References = P639. Chapter 3 fuzzy breakpoints live in code, not the paper.*
