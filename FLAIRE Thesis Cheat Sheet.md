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
| **Benchmark (same split)** | LR 0.9126 · DT 0.9180 · **RF 0.9426** · GB 0.9536 — RF is the defensible default, *not* the top scorer |
| **Chronological split** | **0.8962** accuracy (macro F1 0.8906) vs 0.9426 stratified — confirms the inflation caveat |
| **Label rule (actual)** | Quantile-weighted, cuts ≥1.5 High / ≥0.7 Medium (`add_target_features_only.py`) — reproduces **100%** of the shipped labels |
| **Missing tide in training** | 223 / 1,826 rows (**12.2%**) — no imputation, no row dropping; RF routes NaN natively |
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
| Total cost | **₱27,920** (Table 3.2 — edge station ₱19,050, river node ₱7,070, general materials ₱1,800) |
| Flood events | 4 documented: 21/10/2021, 30/03/2022, 27/12/2022, 23/11/2023 → **2 High / 2 Medium** |
| Forecast horizon | Cached Open-Meteo, 7 days, updated every 6 h |

**Fuzzy water-level breakpoints (current code, `src/config.py`):**
Low < 0.914 m (3 ft) · Medium 0.914–1.219 m · High 1.219–1.829 m · Very High ≥ 1.829 m (6 ft)
Risk transitions: Alarm at 0.914 m (3 ft) · Critical at 1.2192 m (4 ft) — **critical level 1.2192 m, a placeholder pending the barangay's hydrological survey**

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
- "We beat a threshold baseline" — the *threshold-based warning-method* comparison is still future work (P344, P526, P604). We **did** benchmark four model families (LR 0.9126 / DT 0.9180 / RF 0.9426 / GB 0.9536) — that is a different, narrower claim, and RF did not win it.
- "Two sensor nodes" / "monsoon-season campaign" — single node, ~21.5 h (P252)
- "It was tested in a typhoon" — deployment stayed at Receding (P633)
- "RF is the most accurate model" — gradient boosting scored higher (0.9536); RF was the defensible default.
- "The thresholds are 0.61 m / 0.80 m / 2.0 m" — the running system uses 914 / 1,219 / 1,829 mm with a 1.2192 m critical level.
- "The labels came from a composite score of ≥6.0 / ≥3.0" — the shipped labels came from the quantile-weighted rule; the thesis sentence naming those cuts is wrong and must be corrected.
- "The thresholds came from a completed hydrological survey" — they are placeholders pending the barangay's hydrological survey.
- "The fuzzy weights are membership centroids" — they are hand-set design constants in the code.

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
> The RF added a reproducible, edge-executable approximation of our scoring rule — 94.26% agreement. It did not add independent predictive skill; we say so explicitly. The AI layer's value is that it runs offline on a Pi, and its usefulness beyond our scoring rule remains to be shown with independent flood-event labels. *(P250, P603, P606)*
>
> *(Precision: the labels came from a quantile-weighted score over the same features — p50/p75/p90 buckets weighted R7 .30 / R3 .20 / R1 .15 / rain_days .10 / TideMax .10 / TideMin .05 / TMAX .05 / TMIN .05, cut at ≥1.5 High and ≥0.7 Medium. Do **not** describe them as "a composite score of ≥6.0 / ≥3.0" — that sentence is in the printed thesis and it is wrong; those cuts reproduce only 64.2% of the shipped labels, while the quantile-weighted rule reproduces 100%.)*

**Q: "Only 2 of 4 floods were High, and both were ones your rule already flags."**
> Correct. The 94.26% reflects agreement with our own rule, not flood prediction. The four-event check shows the rule-derived labels capture accumulated-rainfall signals but do not reliably encode flood occurrence — which is why independent labels and chronological validation are the top recommendations. *(P538, P603, P606)*

**Q: "Did the system ever actually send an SMS?"**
> SMS is implemented and fires at Alarm and Critical, but the deployment never rose above Receding, so no alert fired in the field. The capability is there; the real-event trigger test is future work. *(P249, P604)*

**Q: "38.5% hit an explicit rule — 61.5% is a hand-weighted fallback. Who validated the weights?"**
> The weights are hand-set design constants in the code (`src/model/fuzzy_logic.py`) — not tuned predictions, and not "membership centroids". We verified functional completeness — all 768 combos and 3,150 grid points return a defined class, output monotonic in water level and rate of rise, no runtime errors. It was not validated against real flood outcomes. *(P480–P482)*

**Q: "Title says January 2026, deployment says October 2026."**
> *(Verify the fix before printing — this is the #1 question and the only one that must be eliminated, not answered.)*

**Q: "What's the cost?"**
> ₱27,920 total (Table 3.2 — edge station ₱19,050, river node ₱7,070, general materials ₱1,800). The Pi 5 is ₱6,500 of it. Low enough for a barangay budget; full table in Chapter 4.

**Q: "Why Random Forest? Why not logistic regression or a decision tree?"**
> We benchmarked four model families on the same stratified split: logistic regression 0.9126, decision tree 0.9180, **Random Forest 0.9426**, gradient boosting 0.9536. So RF did *not* win — gradient boosting was about one point ahead. RF was the defensible default: it is the documented, literature-backed choice for this problem class (Refadah's review; Mesias & Bagtasa for Philippine typhoon-rainfall prediction), its bagged construction suits 1,826 noisy rows with a 918/593/315 class imbalance and 12.2% missing tide, and a 2 MB scikit-learn pickle that infers in milliseconds on a Pi fits a pipeline that runs every five minutes. The narrow spread across four families is itself the finding — the target is a threshold function of the same eight inputs, which is exactly why we report 94.26% as agreement with our own rule rather than as predictive skill. *(P307, P603)*

**Q: "Why combine Random Forest with fuzzy logic? Why not one model?"**
> They are complementary in time, information and audience. The RF works on historical and forecast aggregates (R1/R3/R7, rain days, temperature, tide) for the 24 h and 48 h horizons; the fuzzy layer works on the live state — level now, rate of rise, forecast rain, tide — and consumes the RF propensity as one of its five inputs, so the output is the fusion, not either input. The RF's output is the methodology artifact (metrics, feature importances, confusion matrix); the fuzzy layer's output is the operator artifact (level, rate of rise, rule fired). Each is replaceable independently: with independent flood-event labels we retrain the RF and the rules stay untouched. And honestly — with our current rule-derived labels a rule list would give the same classifications; the hybrid is what lets the model earn its place once real labels exist. *(P240, P224, P606)*

**Q: "What are the thresholds, and where did they come from?"**
> Water-level bands Low < 914 mm (3 ft) · Medium 914–1,219 mm · High 1,219–1,829 mm · Very High ≥ 1,829 mm (6 ft); risk transitions Alarm at 3 ft, Critical at 4 ft; critical level **1.2192 m**. Anchored on PAGASA's 3 ft / 4 ft warning bands, and **placeholders pending the barangay's hydrological survey** — the configuration itself says "Adjust after hydrological survey," and establishing barangay-specific thresholds with the BDRRMC and MDRRMO is a stated recommendation. Never quote 0.61 m, 0.80 m, or 2.0 m.

---

*Paragraph references (P###) point into the current revised file. Abstract is split across P109–P110 (230 words). References = P639. Chapter 3 fuzzy breakpoints live in code, not the paper.*
