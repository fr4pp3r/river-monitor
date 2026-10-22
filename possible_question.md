# FLAIRE Thesis Defense — Possible Questions and Model Answers

> **Numbers verified against the running code on 2026-10-22.** Where a figure below disagrees with the printed thesis, the thesis is wrong and must be corrected before printing. See the three flagged items at the end of this file.

| Fact | Value (verified) |
|---|---|
| Training set | 1,826 daily records, 2020-01-02 → 2024-12-31 |
| Split | Stratified random 80/20 → 1,460 train / 366 test (no cross-validation) |
| RF accuracy | 94.26% (345/366) · macro F1 0.9329 · weighted F1 0.9426 |
| Class distribution | 918 Low / 593 Medium / 315 High |
| **Label rule actually used** | Quantile-bucketed weighted score, cuts ≥1.5 High / ≥0.7 Medium (`add_target_features_only.py`) — **not** the "composite ≥6.0/≥3.0" rule the thesis describes |
| Missing tide in training | **223 of 1,826 rows (12.2%)** — no imputation, no row dropping; RF routes NaN natively |
| **Critical water level** | **1.2192 m (4 ft)** — a placeholder pending the barangay's hydrological survey |
| **Water-level bands** | **914 / 1,219 / 1,829 mm** (3 ft / 4 ft / 6 ft) |
| Fuzzy rule resolution | 768 combos swept, 3,150 grid points; 296 (38.5%) by explicit rule, rest by weighted fallback |
| Fuzzy outputs | Receding / Alert / Alarm / Critical (SMS at Alarm + Critical) |
| Deployment | 13,568 LoRa records, ~21.5 hours, Receding only |
| Acceptability | n=2 BDRRMC focal persons |
| Total cost | ₱27,920 |

---

## A. Problem & Motivation

### Q1. Why did you choose a barangay-level, edge-based approach instead of relying on existing national flood warning systems (e.g., PAGASA)?

PAGASA provides regional forecasts, but barangays like Elvita, Narra, Palawan often receive warnings that are too generalized or arrive too late for local action. FLAIRE was designed to give a specific community a localized, offline-capable decision-support tool that works even when connectivity fails — which is exactly when floods happen. The goal was not to replace PAGASA but to complement it with hyper-local, real-time sensing.

### Q2. What gap in existing flood monitoring does this project address?

Existing systems depend on centralized infrastructure, internet connectivity, and manual observation. FLAIRE addresses the gap of *offline-first, automated, edge-based* flood risk classification at the barangay level — a system that senses, classifies, and alerts without requiring constant connectivity or a human operator watching a gauge.

---

## B. Methodology

### Q3. Why Random Forest? Why not a simpler model like logistic regression or a decision tree?

**Do not claim Random Forest is the most accurate model — it isn't, and we benchmarked it ourselves.** The honest answer is that RF was the defensible default, and here is the comparison we ran (same stratified 80/20 split, `random_state=42`, our exact hyperparameters):

| Model | Accuracy | Macro F1 | F1 (High) | Model size | Inference* |
|---|---|---|---|---|---|
| Logistic Regression | 0.9126 | 0.8974 | 0.8750 | 0.9 KB | 0.20 ms |
| Decision Tree | 0.9180 | 0.9057 | 0.8923 | 20.8 KB | 0.22 ms |
| **Random Forest (shipped)** | **0.9426** | 0.9329 | 0.9160 | 2,041 KB | 13.3 ms |
| Gradient Boosting | **0.9536** | 0.9423 | 0.9173 | 383 KB | 2.04 ms |

*measured on the development PC. The Pi 5 runs the whole pipeline every 300 s, so every model here is comfortably within budget.*

**So why RF, given gradient boosting edged it by about one point?**

1. **It is the documented, literature-backed default for this class of problem.** Refadah's review benchmarks ensembles as consistently strong across flood scenarios; Mesias and Bagtasa used RF for Philippine typhoon-rainfall prediction; Schumacher et al. transitioned an RF system to operations at CSU-MLP. Be honest that the literature is not one-sided: in Kim et al.'s Philippine basin study XGBoost actually beat RF, and in Bibi et al.'s Kabul River study LSTM won — we are not claiming RF dominates the literature either.
2. **Its bagged construction is the right risk profile for our data.** 1,826 rows, 8 mixed-scale features, a 918/593/315 class imbalance, and 12.2% of rows carrying missing tide values. Bagging plus feature subsampling averages away the variance of any single cut, and `class_weight='balanced'` handles the imbalance without resampling. On data this small and noisy we could not afford the extensive tuning gradient boosting needs to stay stable.
3. **Deployment fit.** The RF is a 2 MB pickle, trains offline in scikit-learn, loads with the dependency set the project already uses, and infers in milliseconds on the Pi 5. For a pipeline that runs every five minutes, a one-point gap did not justify abandoning the better-understood, better-documented choice.
4. **The narrow spread across four very different model families is itself the finding.** Logistic regression (0.9126) and gradient boosting (0.9536) land four points apart *because the target is a deterministic threshold function of the same eight inputs*. That is exactly the circularity Chapter 4 discloses — and exactly why we report this metric as rule-consistency rather than predictive skill.

**Second line of defence — the split.** The same model under a chronological 80/20 split gives **0.8962** accuracy (macro F1 0.8906) against 0.9426 under the stratified random split. That ~4.6-point drop confirms the thesis's own statement that a random stratified split over rolling-window features "may inflate apparent generalization performance" — which is why chronological validation is our first methodological recommendation.

**On feature importance:** the R7/R3 dominance is real (R7 0.40, R3 0.24, R1 0.11) and hydrologically sensible, but it is an output of scikit-learn's impurity-based ranking in the training run — the thesis contains no feature-importance table. Do not say "the thesis reports a feature-importance table."

### Q4. Why fuzzy logic for the second stage? Why not just use the RF output directly?

The RF output is a static classification based on historical weather/tide patterns. Flood risk, however, depends on *real-time* conditions — is the river rising right now? How fast? Fuzzy logic fuses the RF propensity with live sensor data (water level, rate of rise, forecast rain, tide) and produces a graded, four-level risk output. It also makes the system interpretable: each rule is a human-readable IF-THEN statement that operators can understand and trust.

**State the honest scope of the rule base before they find it:** the 20 rules (15 core + 5 gap-fill) resolve **296 of the 768 dominant-term input combinations (38.5%)**; the remaining **61.5%** are resolved by a membership-weighted fallback that interpolates rather than jumping at hard thresholds. The defensible characterization is that the fuzzy layer is *partially rule-based* — explicit, readable rules for the dominant flood scenarios, and a transparent weighted scorer for the rest. Graceful degradation was deliberate: a system that errors on an uncovered input is worse than one that interpolates. Completing the rule base is named future work.

Two supporting points:
- **Rule 11 is a safety override**: `Very High water level → Critical` on its own, regardless of rain, tide, or RF propensity. When the inputs disagree, the system errs toward caution.
- **What the operator actually sees**: the dashboard shows the input values, the rule that fired, and a fallback flag. Membership degrees and the crisp defuzzified value exist in the API payload but are not rendered on screen — a UI gap, not a design choice.

**Thresholds to quote — these are the numbers the running system uses:** critical water level **1.2192 m (4 ft)**; water-level bands **914 / 1,219 / 1,829 mm** (3 ft / 4 ft / 6 ft). Do not quote 0.61 m, 0.80 m, or 2.0 m; those are stale figures from an earlier configuration.

### Q4B. Why combine fuzzy logic with Random Forest at all? Why not just use one model?

**They are complementary in time, in information, and in audience — and the thesis says it in one sentence. Quote Chapter 1 nearly verbatim:** "The Random Forest model provides data-driven estimates of flood propensity based on historical and forecast meteorological and tide-related features, while the fuzzy-logic classifier integrates these estimates with the real-time water-level reading, its rate of rise, the cached forecast rainfall, and the tide level using interpretable decision rules. This allows BDRRMC personnel to understand not only the resulting risk level, Receding, Alert, Alarm, or Critical, but also the local conditions and decision logic that contributed to it. Because the final warning decision remains with the BDRRMC, the system functions as a decision-support tool rather than a replacement for human judgment."

Supporting points if pressed:

- **Complementary in time.** The RF runs on historical/forecast aggregates (R1/R3/R7, rain days, temperature, tide) for the 24 h and 48 h horizons. The fuzzy layer runs on the live state — level now, rate of rise, forecast rain, tide — and consumes the RF propensity. The output is the fusion, not either input.
- **Complementary in information.** The RF is blind to the river; the fuzzy layer is blind to the weather regime.
- **Complementary in audience.** The RF's output is the methodology artifact (metrics, feature importance, confusion matrix); the fuzzy layer's output is the operator artifact (level, rate of rise, rule fired). One reviewable variable joins them.
- **Neither alone produces the required output.** RF alone → three propensity classes, no live signal, no Alarm/Critical distinction, and nothing an SMS decision can be justified from. Fuzzy alone → pure expert assumption with no learned component, and with only four documented flood events the rules would carry no empirical grounding at all.
- **Each is replaceable independently.** When independent flood-event labels exist, retrain the RF and the rule system stays untouched.

**The hardest follow-up — "if the RF only supplies one of five fuzzy inputs, is it doing real work?"** Answer honestly; this is already the wording in the Defense Script: *"Right now, for these labels, you'd get the same classifications — we say that in the conclusions. The difference is what happens next: a rule list can only encode what we already wrote down. With independent flood-event labels, the model can learn patterns we didn't hand-code — and because it sits behind the fuzzy layer, we can swap it without touching the transparent decision rules the BDRRMC relies on."*

**"Why not just add water level as an RF feature?"** — the strongest answer we have: *"The training set contains no observed water level at flood time; the levels in it are the output of the scoring rule. Putting live sensor water level into the RF would inject a train/inference mismatch between rule-scored historical levels and real sensor readings, and consuming rate-of-rise would mean retraining every minute. The fuzzy layer absorbs the live signal at inference time with no retraining."*

**"Isn't the hybrid just complexity for its own sake?"** Every component buys a named requirement from the deployment context: offline edge operation (the learned part runs on a Pi), operator trust (expert-readable rules), and SMS-triggered alerting (four actionable levels). Removing either half breaks one of those.

### Q5. Why these eight features? Why not include humidity, wind speed, or soil moisture?

The eight features were selected based on data availability from PAGASA and NAMRIA for the 2020–2024 period, and on their physical relevance to flooding: accumulated rainfall (R1, R3, R7) captures antecedent wetness; rain days capture persistence; temperature and tide capture seasonal and tidal influences. Humidity and wind speed were not consistently available in the historical datasets. Soil moisture would be valuable but requires ground sensors that were not deployed. The thesis recommends expanding the feature set as more data becomes available.

**If pressed on tide specifically:** tide is one of the features with real missingness in the training set — 223 of 1,826 rows (12.2%) have a missing `TideMax`/`TideMin`, and the thesis itself notes that tide- or water-level-driven flooding is not represented by the present feature set. Both are honest answers, and both are in the document.

### Q6. How did you determine the membership function thresholds?

**Quote the running system's numbers, and only those:** critical water level **1.2192 m (4 ft)**; water-level bands **Low ≤ 914 mm, Medium 914–1,219 mm, High 1,219–1,829 mm, Very High ≥ 1,829 mm** (3 ft / 4 ft / 6 ft); rain bands 5 / 15 / 30 mm per day; rate-of-rise bands −0.5 / 0.5 / 4.0 mm per hour; tide bands 0.5 / 1.0 / 1.5 m.

The provenance is PAGASA: the levels are anchored on PAGASA's 3 ft and 4 ft warning bands, expressed as fractions of the critical level (Alarm at 0.75 of critical, Critical at 1.0). The membership functions are then shaped to overlap at the boundaries so transitions are smooth rather than abrupt.

**Say this before they ask it:** these values are **working placeholders, not survey-derived constants.** The configuration carries the note "Adjust after hydrological survey," and establishing barangay-specific thresholds with the BDRRMC and MDRRMO is a stated recommendation. We do not claim a completed hydrological survey.

> ⚠️ **Thesis correction required.** The thesis body currently states "below 0.61 m" and "an alert threshold of 0.80 m" in the field-deployment paragraph, and Chapter 4's label-rule sentence names a rule that was not the one used. See the flags at the end of this file.

---

## C. Validation & Results

### Q7. Your model achieved 94.26% accuracy. Why should we not consider this a strong result?

Because the labels were generated by a scoring rule derived from the same eight features the model uses. The 94.26% reflects the model's ability to reproduce that rule — not its ability to predict actual flood occurrence. The thesis explicitly states this: the accuracy demonstrates consistency with the rule-derived scoring scheme, not independent predictive skill. A high score against circular labels is expected and does not validate the model as a flood predictor.

**Add, if it strengthens the exchange:** we benchmarked four model families against the same labels — logistic regression 0.9126, decision tree 0.9180, Random Forest 0.9426, gradient boosting 0.9536. The whole spread is four points, which is exactly what you would expect when the target is a deterministic threshold function of the same inputs. That narrowness is the circularity made visible, and it is why we frame the metric as rule-consistency rather than skill.

### Q8. The four documented flood events classified 2 as High and 2 as Medium. Is this not evidence the model works?

It is evidence the model reproduces the rule — which is exactly what it was trained to do. The two High events had the strongest rainfall signals (R7 = 142.6 mm and 50.2 mm), and the two Medium events had moderate rainfall (R7 = 35.0 and 40.4 mm). The model matched the rule on all four dates. This is diagnostic: it shows the model mirrors the rule rather than encoding real flood occurrence. The thesis presents this as a preliminary case check, not validation.

### Q9. Why only four flood events? Could you not find more?

The barangay's documented flood records for 2020–2025 contained only four events with sufficient detail to include in the analysis. This is a small sample, and the thesis acknowledges it. Four events are enough for a diagnostic check but not for statistical validation. The thesis recommends establishing a systematic flood event recording protocol at the barangay level to build a larger labeled dataset for future work.

### Q10. One of the four events (30/03/2022) had a missing tide value. How did you handle this?

The missing tide value was noted as a data-quality gap. The thesis flags this as a limitation and recommends correcting the historical dataset before further analysis. The missing tide data does not change the overall finding — the event was still classified High based on its strong rainfall signal.

**Be precise about the mechanism if asked:** no imputation is applied anywhere in the pipeline. The training set itself carries missing tide values — **223 of 1,826 rows (12.2%) have a missing `TideMax`/`TideMin`** — and scikit-learn's Random Forest routes missing values natively per split, so those rows are retained rather than dropped or filled. Say that plainly: it is a property of the dataset and the estimator, not a designed imputation step.

**The larger disclosure to volunteer:** 12.2% of training rows missing tide is a material data-quality fact about the feature set and belongs in the limitations discussion.

---

## D. Field Deployment

### Q11. The deployment was planned for 47 hours but only recorded 21.5 hours. What happened?

The battery depleted sooner than planned. The recorded data spans approximately 21.5 hours, beginning October 11 at 9:46 PM and ending approximately 21.5 hours later. The difference between the intended and actual deployment duration is noted as a limitation — possibly due to battery capacity, sensor power draw, or clock configuration. The thesis recommends verifying the Raspberry Pi clock and power management in future deployments.

### Q12. The river never rose above Receding during the deployment. Does this mean the alert system is untested?

The field deployment validated the sensor-and-logging pipeline under real conditions — 13,568 LoRa records were captured and transmitted successfully. The alert path was tested separately in the functional verification (Table 4.3), where all four risk classes were exercised with defined inputs and produced expected outputs. What the deployment could not test is whether the system correctly escalates during a real flood — and the thesis says so explicitly, naming it as a validation gap that only a future flood event can close.

### Q13. The dataset contained anomalies — 67 zero-distance records, 124 negative water levels, and implausibly short distances. How do you know the sensor data is reliable?

The anomalies were flagged for quality review rather than interpreted as actual river-level changes. Excluding these records, the water level remained between 0.01 m and 0.18 m — entirely within the Low band. The anomalies are consistent with a dangling wire or sensor interference, and the thesis recommends hardware inspection. The key point is that the system correctly identified and isolated these anomalies rather than treating them as valid readings.

---

## E. System Design

### Q14. Why offline-first? Why not just send all data to the cloud?

Floods often damage infrastructure and disrupt connectivity. An offline-first system continues to sense, classify, and alert even when the internet is down — which is precisely when warnings are most needed. FLAIRE caches weather and tide forecasts, processes everything locally on the Raspberry Pi, and only requires connectivity for SMS alerts. This makes it resilient in the exact conditions where it is most needed.

### Q15. The fuzzy layer's fallback path fires often — many inputs don't hit a real rule. Does this weaken the interpretability claim?

The fallback exists because the 20-rule base was designed around the most common flood-relevant combinations, not every possible input. When no rule fires, the system uses a membership-weighted scoring heuristic that interpolates smoothly rather than failing silently. This is a deliberate design choice — a fuzzy system that crashes on uncovered inputs is worse than one that degrades gracefully. The honest characterization is that the fuzzy layer is partially rule-based: it produces interpretable, rule-driven outputs for dominant flood scenarios and falls back to a transparent scoring heuristic for edge cases. A complete rule base is future work.

**Two additions for accuracy:** the fallback weights are **hand-set design constants in the code** (`src/model/fuzzy_logic.py`), not tuned predictions and not "membership centroids" — do not use that phrase. And the **rule number shown on the dashboard is a dominant-term attribution**, computed by matching each variable's highest-membership term against a lookup table, not an instrumented trace of the engine's activated rule. If an examiner reads the code, say it plainly rather than letting them find it.

### Q16. Why a Raspberry Pi? Why not a microcontroller like an Arduino?

The Raspberry Pi 5 was chosen because it has sufficient processing power to run the Random Forest model and fuzzy inference locally, supports Python (which the ML stack requires), can interface with LoRa and SMS modules, and can cache weather data. An Arduino would be lower power but cannot run scikit-learn or skfuzzy. The trade-off is higher power consumption — which is why the battery limitation was encountered — but the computational capability is necessary for the on-device AI pipeline.

---

## F. Acceptability & Impact

### Q17. Only two focal persons rated the system. Is this sufficient evidence of acceptability?

Two ratings are not statistically generalizable, and the thesis labels them as preliminary acceptability findings, not validation. However, the purpose was to establish that the system is usable by its intended operators — two BDRRMC focal persons are the actual end users. Their 5.00 ratings on functionality, reliability, and intention to use show the system is not rejected at the point of need. A larger survey is future work, but for a feasibility study, demonstrating initial acceptability among target users is sufficient.

### Q18. What is the practical contribution of this research to the barangay?

The contribution is a documented, reproducible implementation of an offline-first, edge-based flood decision-support system — together with an honest account of its limitations. The barangay now has a working prototype that senses water level, classifies flood risk, and can send SMS alerts. More importantly, the thesis provides a clear roadmap for establishing real predictive skill: independent flood-event labels, water-level-aware features, and chronological validation.

### Q19. If you had more time and resources, what would you do differently?

Three things: (1) Install the water-level sensor for a full flood season to capture real water-level data during flood events — this would enable independent labels and break the circularity. (2) Expand the barangay flood event recording protocol to build a larger labeled dataset. (3) Conduct a larger acceptability survey with more BDRRMC focal persons and operators. The thesis identifies all three as concrete future work.

---

## G. Broader Significance

### Q20. How does this research contribute to the broader field of flood monitoring?

FLAIRE demonstrates that an offline-first, edge-based AI system for flood decision support is technically feasible at the barangay level with locally available data and open-source tools. The two-stage architecture (Random Forest + fuzzy inference) is generalizable to other riverine communities with similar data constraints. The honest documentation of limitations — circular labels, limited field validation, small acceptability sample — provides a transparent template for other researchers working in data-scarce environments.

---

## Quick-Reference Summary

| Theme | Key Message |
|---|---|
| **Motivation** | Complement PAGASA with hyper-local, offline-capable decision support |
| **Methodology** | RF is the defensible default, not the top scorer (LR 0.913 / DT 0.918 / RF 0.943 / GB 0.954); fuzzy for real-time fusion and interpretability |
| **Validation** | 94.26% is rule agreement, not predictive skill; chronological split gives 0.8962; four events are diagnostic |
| **Deployment** | Pipeline validated; alert path tested separately; flood escalation untested |
| **System design** | Offline-first for resilience; fallback for graceful degradation |
| **Acceptability** | Preliminary, not generalizable — but shows target users will use it |
| **Contribution** | Feasible system + honest limitations + clear path to real validation |

---

## ⚠️ Three items to correct in the printed thesis

**1. The label rule (Chapter 4, RF evaluation results).** The thesis says:

> "A composite score incorporated one-day, three-day, and seven-day rainfall; number of rainy days; maximum and minimum temperature; and maximum and minimum tide levels. **Scores of at least 6.0 were labeled High, scores of at least 3.0 were labeled Medium, and scores below 3.0 were labeled Low.**"

Recomputing both generators against the shipped `training_data4.csv`:

| Generator | Reproduces the shipped labels? | Class distribution it yields |
|---|---|---|
| Composite, ≥6.0 / ≥3.0 (what the thesis describes) | **1,172 / 1,826 = 64.2%** | 506 / 1,125 / 195 |
| Composite, best possible cut pair (4.0 / 5.5) | 1,478 / 1,826 = 80.9% | — |
| **Quantile-weighted, ≥1.5 / ≥0.7 (`add_target_features_only.py:105-137`)** | **1,826 / 1,826 = 100.0%** ✅ | 918 / 593 / 315 = shipped |

The labels were produced by the **quantile-weighted** variant: each feature bucketed at its p50/p75/p90, weighted (R7 0.30, R3 0.20, R1 0.15, rain_days 0.10, TideMax 0.10, TideMin 0.05, TMAX 0.05, TMIN 0.05), multiplied 1/2/3 by bucket, cut at ≥1.5 High and ≥0.7 Medium. The "94.26% = agreement with the rule" framing survives intact — it is still a threshold-based score over the same eight features — but the *named* rule must be the rule that actually ran.

**2. The fuzzy water-level bands (Chapter 4, field deployment).** The thesis says the observed 0.01–0.18 m range "lies entirely within the lowest (Low) water-level band of the fuzzy-logic classifier (below 0.61 m) and well below the alert threshold (0.80 m)". The running system uses **914 / 1,219 / 1,829 mm** with a **1.2192 m** critical level. The paragraph's *conclusion* (the deployment stayed in the Low band and never reached Alert) remains true under either set — only the numbers need fixing.

**3. Threshold provenance.** Do not claim the thresholds came from the local hydrological survey. `src/config.py` says "Adjust after hydrological survey," and establishing barangay-specific thresholds is a stated recommendation. Say: anchored on PAGASA's 3 ft / 4 ft warning bands, to be finalized with the barangay's hydrological survey.
