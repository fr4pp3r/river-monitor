# FLAIRE — Oral Defense Script & Q&A Playbook

**How to use this document.** Part 1 is your opening — rehearse it until it sounds conversational, not read. Part 2 contains the five questions most likely to decide the defense, each with a verbatim answer to practice aloud. Part 3 is the full question bank by category. Paragraph references (P###) point into the current revised file (828 paragraphs — References is now **P639**; conclusions/recommendations after P606 shifted +1). **Never read the refs aloud** — they are only for you to find the page fast. **Part 3-H is the proposal-to-thesis delta** — the questions that only exist if a panelist has read your *accepted proposal*. Full evidence for every one of them is in the companion file `FLAIRE Proposal-to-Thesis Change Log.md`. Part 4 is the never-say list. Part 5 is the co-author cheat sheet. Part 6 is the strategy for questions nobody prepared for.

---

## Part 1 — Opening Statement (≈90 seconds)

> FLAIRE — Flood Level AI Risk Evaluation — is an offline-first flood early-warning prototype for Barangay Elvita in Narra, Palawan. The problem there is specific: warnings come from municipality-wide advisories that don't say whether *this* barangay is affected, and connectivity drops exactly when warnings matter most.
>
> The system is a solar-powered sensor node that measures river level and rainfall and sends them by LoRa radio to a Raspberry Pi 5 — no internet required. On the device, a Random Forest model estimates flood propensity from eight meteorological and tide features, and a 20-rule fuzzy-logic classifier combines that propensity with the live water level, its rate of rise, cached seven-day weather and tide forecasts, and the tide, to produce four risk levels: Receding, Alert, Alarm, and Critical — shown on a LAN dashboard, with SMS alerts at the two highest levels. The whole build costs about ₱23,700.
>
> The study designed, developed, and *initially* evaluated the system: a functional verification of the fuzzy layer, a check against four documented flood events, a field deployment of about 21.5 hours, and an acceptability rating by two BDRRMC focal persons.
>
> Our central finding is deliberately honest. The system is technically feasible as an offline-first, edge-based decision-support tool — but its predictive skill is *not yet established*: the model was evaluated against labels derived from the same eight features, and on the four documented floods it simply reproduced its own scoring rule's verdict — flagging the two strongest-rainfall events and missing the two with moderate rainfall. The thesis states this plainly in the abstract and conclusions, and specifies exactly what is needed next: independent flood-event labels, water-level and tide-aware features, and chronological validation.

**Delivery note:** say "initially evaluated" and "not yet established" with confidence, not apology. The honesty *is* the strongest part of this thesis.

---

## Part 2 — The Five Questions That Matter Most

### Q1. "Your labels came from the same eight features the model was trained on, and on the four real floods the model just agreed with your own rule. What did the Random Forest actually add?"

*(This is the #1 panel question. Answer verbatim, then stop talking.)*

> "Three things, and I'll be precise.
>
> First, it was a stated aim, not an assumption. Chapter 1 says the study set out to explore whether machine-learning models can be used to assist in assessing flood risk at the barangay scale. We treated that as an open question, and Chapter 5 answers it: feasibility is established — a model can be trained on eight features and run on a Raspberry Pi and reproduce our decision rule with 94.26% agreement — but predictive usefulness beyond the composite score is not established, for exactly the reason you've raised.
>
> Second, architecturally it's a replaceable layer: the Random Forest supplies the flood-propensity input that the fuzzy classifier consumes alongside the live water level, rate of rise, forecast rainfall, and tide. When independent flood-event labels exist, we retrain that model without touching the rule system — that's our first recommendation in Chapter 5.
>
> Third, the honest concession: because the labels came from the same eight features, as currently labeled the rule alone would produce the same classifications. The four-event check bears this out: the model's verdict matched our rule on all four documented floods. So the model's value today is what it enables once real labels exist — and the thesis was written to say exactly that, rather than to claim a prediction skill we didn't demonstrate."

**Follow-up — "Why include it at all, then?":**
> "Because you can't answer the question 'can ML help?' without building and evaluating it. The architecture keeps the answer open: the fuzzy layer's transparency serves the BDRRMC today, and the ML layer can earn its place as the labels improve. The literature — Refadah's review of ML for flood prediction — supports ensemble methods as the standard choice, so we implemented the recommended approach and evaluated it honestly."

*(ref: P224, P307, P371, P606, P622)*

### Q2. "Only two of your four documented floods were classified High — and both were the ones your own rule already flags. Why should the BDRRMC trust this system?"

> "Because the thesis never asks them to trust a prediction the system hasn't made. FLAIRE is decision-support: the BDRRMC confirms every public alert — the system does not act as an autonomous warning authority. On the four-event result itself, we report it in the abstract and in the conclusions: the model classified two of the four documented floods as High — exactly the two with the strongest accumulated-rainfall signals, which are the two our own scoring rule already flags — and the other two as Medium. That is diagnostic rather than reassuring: it shows the model mirrors the rule, and that our feature set represents rainfall rather than floods, since the two misses carried only moderate rainfall. That is precisely why we recommend tide- and water-level-aware features plus independent labels before any claim of real flood identification. The deployment that was performed never claimed flood prediction — it validated the sensor-and-logging pipeline under low-water conditions, and we say so."

*(ref: P587, P605, P606, P622, P632, P633)*

### Q3. "Chapter 3 says the system automatically sends SMS. Did any SMS ever actually get sent?"

> "SMS is implemented and enabled on the deployed unit. It triggers only at the Alarm and Critical levels. During the field deployment the river never rose above the Receding level, so no alert condition occurred and no SMS was sent — correctly so; the system did not fire alerts that weren't warranted. The thesis describes SMS as notification support in the abstract, and delivery queuing with confirmation is listed as a system improvement. So: the capability works, the field test didn't exercise it, and the document claims neither more nor less than that."

**Backup if pressed on evidence:** "The deployed Raspberry Pi configuration has SMS enabled — I can show the configuration; the development copy in the repository has it off by default, which is a safety default for local testing."

*(ref: abstract, P377, P618, P633 — repo fact: `SMS_ENABLED` is `False` in the development config, `True` on the device)*

### Q4. "38.5% of combinations hit an explicit rule — so 61.5% of your fuzzy layer is a hand-weighted fallback. Who validated those weights?"

> "Two answers. First, the thesis discloses the split explicitly — 296 of 768 dominant-term combinations resolved by an explicit rule, the remainder by the membership-weighted fallback, whose purpose is to guarantee a defined output whenever no rule fires. Second, all four representative outputs in Table 4.3 — the cases we present as evidence — correspond to explicit rules 1, 4, 6, and 8; they are not fallback cases. The fallback weights themselves are documented design constants, and evaluating the fuzzy classifier separately against documented flood conditions and BDRRMC-validated thresholds is a stated recommendation — so yes, that validation is named as future work rather than claimed as done."

*(ref: P530, Table 4.3, P625)*

### Q5. "The title page says January 2026. Your deployment data says October 2026. Which is it?"

**Primary answer: fix the document — this question must never be asked.** If it survives:

> "That's a document error on the title page — the work and deployment were completed in 2026 and the corrected copy reflects the actual date. It should not have reached the panel as printed, and we've corrected it."

*(ref: P44 vs P503 — **verify the fix before printing.**)*

### Q6 — the proposal-reading panelist

Assume at least one panelist has read your *accepted proposal*, because if they have, the sharpest question available to them is why RQ3 changed from a threshold comparison to a rule-consistency check. That is answered in **Part 3-H, H1**. Rehearse it with the other five — it is a sixth question in all but name.

---

## Part 3 — Question Bank

### A. Concept & Architecture

**A1. What does FLAIRE stand for and what does it do?**
> "Flood Level AI Risk Evaluation. It monitors river level and rainfall locally, classifies flood risk into four levels — Receding, Alert, Alarm, Critical — and presents that to the BDRRMC on a local dashboard, with SMS at the highest levels. It's decision-support: the barangay makes the call." *(P223)*

**A2. Why "offline-first"? Why LoRa?**
> "Because rural connectivity fails exactly when warnings matter. LoRa gives us low-power, kilometers-range transmission from the river to the barangay hall without internet; everything after that — storage, classification, dashboard — runs on the local device. Internet is only needed to refresh the cached forecasts." *(P220, P223, P288)*

**A3. Why both a Random Forest *and* fuzzy logic? Why not just one?**
> "They do different jobs. The Random Forest estimates meteorological flood propensity from eight features — something a rule list handles poorly as interactions grow. The fuzzy classifier handles the real-time hydrology — water level, rate of rise — with explicit, readable rules the BDRRMC can follow, which a black-box model can't offer. The hybrid keeps the final decision layer interpretable while the machine-learning layer stays replaceable." *(P240)*

**A4. Is fuzzy logic AI? Why call this AI-enhanced?**
> "Fuzzy inference is a branch of computational intelligence, and the system contains a trained machine-learning model as well. 'AI-enhanced' describes the hybrid pipeline as a whole — trained model plus fuzzy inference — running at the edge." *(P223, P241)*

**A5. Why four risk levels? Who decided the thresholds?**
> "Receding, Alert, Alarm, Critical — mapped to the barangay's operational reality. The levels come out of the fuzzy rule base — 15 core rules plus 5 gap-fill rules, 20 total — combined with membership functions over water level, rate of rise, forecast rainfall, and tide. The rules are disclosed in full in Chapter 3, so the barangay can audit every decision path." *(P232, Table 3.1)*

**A6. How current is the forecast data?**
> "Cached from OpenMeteo, refreshed at least daily — targeted every six hours when internet is available — and stored in a local database so classification never depends on connectivity at decision time." *(P230)*

**A7. What happens when the internet is down?**
> "Nothing changes for classification — the model and rules run locally on cached data. Only the forecast refresh ages; the dashboard, storage, and alerts are LAN-local."

**A8. Why a Raspberry Pi 5? Could it run cheaper/smaller?**
> "It fits the budget and the workload — running a scikit-learn Random Forest plus a fuzzy inference loop plus a local web server is beyond a bare microcontroller, at ₱6,500 it's a third of the hardware cost, and it keeps the whole stack in Python so the research code and device code are the same code." *(cost table, P463)*

### B. The AI/ML Cluster

**B1. See Part 2, Q1 — the composite-score question.** (Highest value; rehearse until automatic.)

**B2. "Why not just run the composite score directly?"**
> "Right now, for these labels, you'd get the same classifications — we say that in the conclusions. The difference is what happens next: a rule list can only encode what we already wrote down. With independent flood-event labels, the model can learn patterns we didn't hand-code — and because it sits behind the fuzzy layer, we can swap it without touching the transparent decision rules the BDRRMC relies on."

**B3. Why Random Forest specifically?**
> "Refadah's review of ML for flood prediction benchmarks ensembles as consistently strong across the scenarios reviewed, and Random Forest is the standard, well-understood ensemble — robust to mixed features, interpretable enough via feature importance, and light enough for a Raspberry Pi. It was the defensible default." *(P307)*

**B4. Is 94.26% good? Is your model accurate?**
> "94.26% is weighted accuracy against rule-derived labels — it measures consistency with our own scoring rule, not flood-prediction skill. The thesis says this in the abstract. So the accurate statement is: the model reproduces the rule reliably; predictive accuracy against real floods has not been established."

**B5. Why a random 80/20 split instead of a time-based split?**
> "We used a stratified split to preserve class balance in a small dataset — and the thesis flags chronological validation as the correct method for time-ordered data and lists it as a recommendation. That's an acknowledged limitation, not an oversight." *(P623)*

**B6. What are the eight features, and are they observed or forecast?**
> "R1, R3, R7 — rainfall totals for the previous one, three, and seven days — rainy days, maximum and minimum temperature, and maximum and minimum tide. The rainfall features blend observed sensor history with the cached forecast for the reference day; temperature and tide come from the cached forecast — that's what Chapter 1 means by 'historical and forecast' features. The variables are defined in Chapter 3." *(P223, P405–P411)*

**B7. Your training data was 2020–2024 but the deployment was 2026 — did you retrain?**
> "The model was trained on the 2020–2024 PAGASA/NAMRIA historical set — 1,826 daily records — and deployed as-is; the deployment was a systems test of the pipeline, not a model-retraining exercise. Retraining with newer data and independent labels is part of the improvement path." *(P622, P623)*

**B8. What is the composite score / how were labels created?**
> "A hand-written scoring rule over the same eight features produced Low/Medium/High labels in the training data. That circularity is exactly why we frame E1 as rule-consistency, not prediction — it's disclosed in the abstract, RQ3's wording — 'how consistently does the model reproduce the rule-derived categories' — and the conclusions." *(P234, P603, P606)*

### C. Evaluation & Numbers

**C1. What does E1 — the functional verification — actually prove?**
> "That the fuzzy classifier is functionally complete: across all 768 dominant-term combinations it returns a sensible, defined output — 38.5% through explicit rules, the rest through the guaranteed fallback. It's a functional verification of the fuzzy layer, explicitly not evidence of accuracy against actual floods — the thesis says that sentence outright." *(P530)*

**C2. What did the four-event check (E2) show and what is it worth?**
> "Two of the four documented floods were classified High and two Medium — and on all four the model's verdict matched our own rule. It's a preliminary case check, not an external validation — four events is too thin for either. What it *is* worth is diagnostic: it shows the model reproduces the rule rather than encoding real flood occurrence, and that floods without a heavy-rainfall signal — including tide-driven ones — are invisible to a rainfall-centred feature set. Both drive our recommendations." *(P250, P537, P587, P622)*

**C3. Your deployment was supposed to be longer — what happened?**
> "The battery depleted; the recorded dataset spans about 21.5 hours with 13,568 records. The thesis reports this plainly, flags a clock discrepancy between recorded and reported start times, and recommends power improvements, timestamp documentation, and a repeat deployment as the path to sustained operation." *(P542, P607, P619, P621)*

**C4. Why were there anomalous readings — 2.5 m jumps, negative levels?**
> "Sixty-seven zero-distance readings, 124 negative levels, five implausibly short distances — all flagged for quality review rather than interpreted as river behavior. Root causes are sensor mounting, cable movement, and missing invalid-reading handling — each has a specific recommendation: harden the mount, add validation logic that quarantines bad readings, keep raw values for audit." *(P590, P615, P616)*

**C5. Two respondents isn't a sample. Why should we care about the acceptability ratings?**
> "We agree — the thesis calls the results preliminary and says they should not be generalized at every turn. Two BDRRMC focal persons is the entire relevant population for a system whose operators are the barangay disaster committee. It's initial evidence the instrument and the interface work, and expanding the respondent pool is a stated recommendation." *(P431, P610, P631)*

**C6. How was the survey designed? Was it validated?**
> "A TAM-based instrument — six dimensions: functionality, usability, perceived reliability, contribution to preparedness, attitude, intention to use — five-point Likert, full instrument in Appendix C, 24 items. It was reviewed by subject-matter experts and pilot-tested before administration." *(P440–P448, Appendix C)*

**C7. Why is usability 4.75 and everything else 5.00?**
> "Usability had one lower response among the item ratings — the two focal persons were slightly less emphatic there than on the other five dimensions. It's reported item-honestly rather than rounded up." *(Table 4.6, P569)*

**C8. Perceived reliability was 5.00 but the battery died — isn't that contradictory?**
> "They're different measures and the thesis explicitly juxtaposes them: perceived reliability is what the users experienced in a demonstration; the deployment findings show the hardware has power and sensor issues to fix. The document refuses to let the rating hide the deployment data." *(P570)*

**C9. What statistical treatment did you use?**
> "Accuracy, precision, recall, and F1 per class plus macro and weighted averages on the held-out set — a stratified 80/20 split of 1,826 records. No inferential statistics: with n=2 respondents, reporting means of the Likert ratings is the honest ceiling, and we label them preliminary." *(Ch4 results tables, Table 4.6)*

### D. Methodology & Scope

**D1. Why purposive sampling?**
> "The study needed respondents with direct knowledge of barangay flood conditions and existing warning practices — BDRRMC focal persons. That's the definition of purposive sampling, and it's justified in Chapter 3." *(P431)*

**D2. What were your research questions?**
> *(Know all five cold — P228–P236: problems in current practices; design of the AI-based system with its four components; RF consistency with rule-derived categories; field-deployment performance; acceptability to focal persons.)*

**D3. Is "can ML assist flood-risk assessment" one of your research questions?**
> "It's a stated aim of the study — Chapter 1 says the study explores whether machine-learning models can be used to assist in assessing flood risk at the barangay scale. RQ3 operationalizes the feasibility half by asking how consistently the model reproduces the rule-derived categories, and Chapter 5 answers the usefulness half plainly: not yet established. We deliberately kept five top-level questions rather than splitting a aim into a sixth."

**D4. What was out of scope, and why?**
> "Forecast lead-time measurement and a threshold-baseline comparison — both require event data and a comparison design the four documented events couldn't support. The four-event work is presented as a preliminary case check, and both full evaluations are concrete recommendations." *(P250, P626)*

**D5. Where is your Gantt chart / why does the timeline look like this?**
> *(Have the final Gantt filled to match the narrative at P451/P460 before the defense. Answer: planned phases — planning, design, development, testing, deployment, evaluation — with the deployment in the evaluation window.)*

### E. Limitations, Honesty & Traps

**E1. "Early warning" — you never measured lead time. Why use the term?**
> "The name describes the system's function — it issues warnings when risk reaches Alert, Alarm, or Critical — not a validated forecast horizon. The thesis explicitly does not claim measured lead time; it says the evaluation does not establish lead time, and measuring it against documented events is a recommendation. We were careful to distinguish the two." *(P604, P624)*

**E2. "Chapter 2 says ML offers improved lead time" — so do you claim it or not?**
> "That's a statement of the literature's promise — the background rationale for why these technologies are worth investigating. This study's own claims are governed by what we measured, and we state plainly that no lead time was measured. The background and the findings are doing different jobs."

**E3. The deployment dataset starts 13 hours before the reported installation time. Explain.**
> "We caught and disclosed it — the recorded data begins about 13 hours before the reported installation, which points to the Pi's clock, timezone, or the export process. The thesis states the available dataset must not be extended or relabeled to fit the intended duration, and timestamp synchronization with documentation is a recommendation." *(P542, P621)*

**E4. Was an SMS ever received by a real person?** → Part 2, Q3.

**E5. What are the biggest limitations?** *(Answer fast and completely — this is a gift.)*
> "Four: labels derived from the same features, so no independent prediction validation; a 21.5-hour deployment that never exercised the higher risk classes; sensor and power reliability issues; and n=2 on acceptability. All four are in the conclusions with recommendations attached." *(P603–P610)*

**E6. What would you do with another six months?**
> "Independent flood-event labels from BDRRMC/MDRRMO records, tide and water-level features in the model, chronological validation, a longer powered deployment with multiple sensor nodes, and a baseline comparison — all written out as recommendations in Chapter 5, plus SMS delivery queuing and power hardening." *(P622–P630)*

### F. Practical, Cost & Ethics

**F1. What does it cost?**
> "₱23,700 total — Raspberry Pi 5 at ₱6,500, three LoRa boards at ₱5,400, sensors, enclosure, solar kit, SIM and SMS load, transportation and documentation. Low enough for a barangay budget, and the cost table is in Chapter 4." *(cost table, P463)*

**F2. Can other barangays use it?**
> "Yes — that's the policy-level claim: the architecture is modular and internet-independent, so it can be adapted to other flood-prone communities, with the caveat that the pilot was one barangay and one deployment." *(P242)*

**F3. Who maintains it? What happens when it breaks?**
> "The BDRRMC focal persons are the intended operators — that's who the acceptability study targeted — and maintenance items (sensor mounting, battery, rain-gauge validation, timestamp checks) are concrete recommendations. Honest answer: a maintenance SOP is part of the recommended next step, since the deployment surfaced those failure modes."

**F4. Ethical considerations? Any personal data?**
> "The system monitors river and weather conditions, not people — no personal data is collected by the device. Survey responses are from two officials, reported at dimension level with no individual identifiers. Institutionally: [confirm your ethics/clearance requirement with your adviser before the defense — do not improvise this answer]."

**F5. Does it work during a typhoon — the real scenario?**
> "That's exactly what the deployment didn't cover — the water stayed low, so we validated the pipeline, not the flood conditions. The thesis says Alert, Alarm, and Critical must be exercised in a repeat deployment before operational use. We won't claim a typhoon test we didn't do." *(P633)*

### G. Administrative & Related Work

**G1. What is your contribution / what did each member do?**
> *(You must agree on a truthful division before the defense — see Part 6. Suggested frame for you as primary researcher: "I was the hands-on developer — system architecture, firmware, model training, deployment, and evaluation — with my co-authors contributing in [literature/documentation, field coordination and data gathering, survey administration, testing support]." Every member must be able to describe their own contribution in one sentence.)*

**G2. How is this different from DOST-ASTI's flood early warning systems?**
> "Existing FEWs transmit sensor data to centralized servers accessed through web platforms — which degrades exactly during network outages common in rural areas during typhoons. FLAIRE's differentiator is the offline-first design: classification, dashboard, and alerting all run locally, with cached forecasts and LoRa, at barangay rather than regional scale." *(P220, P222)*

**G3. What is the novelty of this study?**
> "The integration, at barangay scale: cached weather and tide forecasts, real-time LoRa sensing, a hybrid Random Forest–fuzzy pipeline on local hardware, and offline-capable alerting in one modular architecture — plus an honest evaluation methodology that measures rule-consistency and says what it does not prove. The academic contribution is a documented, reproducible implementation with its limitations written down." *(P222, P241)*

**G4. What related work most influenced you?**
> "Refadah's review for the case of ensemble ML in flood prediction; the GSMA report on early-warning systems in the Philippines for the offline-first, fragmentation argument; and LoRa/LoRaWAN technical literature for the radio layer. *(Use whatever two you know cold — do not cite years you can't see.)*" *(P282, P288, P307)*

**G5. Is your bibliography complete?**
> *(It must be — with every in-text citation year filled. If the References section or the Chapter 2 citation holes are still blank, this question is a guaranteed loss. See Part 6 checklist.)*

### H. Proposal vs. Thesis — the delta

These only exist if a panelist has read your *accepted proposal*. Assume one has. The proposal promised more than the thesis delivers, and **every gap is already documented in the thesis itself** — so the answer is always the same shape: *we narrowed this deliberately, here is the reason, here is where it is written down.* Never surprise, never invention. Evidence for each: `FLAIRE Proposal-to-Thesis Change Log.md`.

**H1. "Your proposal's third research question asked you to compare your model against a traditional threshold-based warning method, using accuracy, precision, recall, F1-score, false alarm rate and lead time. Your thesis asks something else. Did you move the goalposts?"** *(This is the delta's #1 question — rehearse it like a Part 2 question.)*
> "The question changed because we could not build the comparison it depended on, and the document says so in three places. Chapter 3 states that the comparison with a traditional threshold-based method was not completed and is identified as future work; it also explains why — the provincial FEWS previously installed in Brgy. Elvita was not operational, standardized, or formally documented during the study, so there was no defensible threshold baseline to compare against. Chapter 1 lists lead-time measurement and the threshold baseline as outside the study's scope. What we *could* do was test whether the model reproduces our own rule-derived labels, so RQ3 asks exactly that — and the results are reported as consistency, not as flood-prediction accuracy. The original comparison was not quietly dropped: it is a named recommendation in Chapter 5."

**H2. "You promised false alarm rate and lead time as evaluation metrics. You report neither."**
> "Correct — and the thesis never reports them. False alarm rate needs a series of real alert decisions scored against real outcomes, and during the field deployment the river never rose above Receding, so no alert ever fired and there was nothing to score. Lead time needs events with known onset times, and we had four documented events — too few to measure a horizon from. That is why we present the four-event work as a preliminary case check and not a validation. Both metrics are named as future work rather than left looking like oversights."

**H3. "Your proposal says two LoRa sensor nodes and data collected across the 2026 monsoon season. You have one node and about a day."**
> "Both reductions are stated in the thesis. Chapter 1 limits the study to a prototype deployment using a single sensor node and says outright that it does not provide full river-system coverage. The deployment was a pilot to prove the whole chain — sensor to edge device to classification to log — not to characterise the river across a season. The recorded dataset is 13,568 records over roughly 21.5 hours before the battery depleted, and we report that duration plainly rather than implying a longer campaign."

**H4. "You proposed to survey BDRRMC personnel, barangay officials and flood-affected residents. You ended with two people."**
> "We narrowed to BDRRMC focal persons, chosen purposively as the people who actually operate the system and make the alert call — they are the relevant population for an operator-facing prototype. The thesis states the ratings are preliminary feedback from key local disaster-risk personnel and explicitly says they should not be generalized to all barangay officials or residents. Expanding the respondent pool is one of our recommendations." *(Also see C5.)*

**H5. "Your proposal promised multi-channel alerts — sirens, queued SMS, social media. Your thesis has SMS and a dashboard."**
> "The system sends SMS at Alarm and Critical and presents everything on the LAN dashboard. Siren activation and social-media posting are described as BDRRMC actions rather than system outputs, because final public alert dissemination stays with the barangay — that is the decision-support framing the thesis uses throughout. Store-and-forward SMS queuing with delivery confirmation is carried in the recommendations."

**H6. "You promised a 24–48-hour predictive decision window. Where is it?"**
> "Removed, because we never measured it. What the system actually has is a cached seven-day forecast horizon — that is the span of forecast data available to it, not a validated warning horizon. Chapter 1 says the system draws on cached forecasts up to seven days ahead, and nowhere does the thesis claim a measured lead time." *(Also see E1 and E2.)*

**H7. "Your proposal title said 'AI Offline-First'. Your thesis title dropped 'AI'. Why?"**
> *(Have one line ready and use the same line every time. Note the tension: the acronym still expands to Flood Level **AI** Risk Evaluation, and the abstract still says "two-stage artificial-intelligence pipeline". If the file is reprinted, resolve the title/acronym disagreement so the page cannot contradict you.)* A4 covers the "is fuzzy logic AI?" half of this.

**H8. "The proposal had one author. The thesis has five. What changed?"**
> *(Do not improvise this. Agree one truthful sentence with all five members and have every one of them say the same thing. See G1 and the Part 6 checklist.)*

**H9. "You switched forecast providers, dashboard frameworks and hardware — OpenWeatherMap to Open-Meteo, Flask to FastAPI, an ESP32 and Raspberry Pi 4 build to Adafruit RFM9x boards and a Pi 5. Why?"**
> "Those are implementation decisions made during development, and the thesis documents the architecture that was actually built and piloted rather than the proposed one. The consequential change is cost: moving to Open-Meteo removed the paid weather-API line entirely, and the total came down from ₱28,200 in the proposal to ₱23,700 in the thesis. The rest is componentry the pilot actually ran."

**H10. "Your proposal said the sensor transmits every 10 minutes. Chapter 3 says every 5 seconds."**
> *(**Verify the deployed firmware's actual sampling and transmission interval before the defense and make the text match it** — do not answer this from memory. Five-second and ten-minute intervals imply very different power budgets, which matters because the deployment ended when the battery depleted.)*

---

## Part 4 — Never-Say List

**Never claim:**
1. The system predicts or forecasts floods — *94.26% is rule-agreement; say so.*
2. Any lead time was measured — *no 24–48 hour window, ever.*
3. An SMS was sent or received during the deployment — *capability yes, field exercise no.*
4. The deployment lasted two days — *21.5 recorded hours, battery depleted.*
5. Alert/Alarm/Critical were validated in the field — *only Receding was observed.*
6. The acceptability results represent the community — *two focal persons, preliminary.*
7. The four-event check was a validation — *a preliminary case check.*
8. The system is autonomous — *decision-support; BDRRMC confirms every public alert.*
9. The fallback weights were validated — *they're documented design constants.*
10. The model was trained or tested on flood events — *it was trained on rule-derived labels.*
11. The threshold comparison was completed — *it was not; it is future work (P250, P344).*
12. False alarm rate or lead time were measured — *neither was: no alert ever fired, and no forecast horizon was measured.*
13. Two sensor nodes were deployed — *one node, and the thesis says so (P252).*
14. The deployment covered a monsoon season — *roughly 21.5 recorded hours (P542).*
15. A co-author can describe another member's contribution — *each member answers only for their own.*

**Never improvise:** numbers, dates, citation years, statistics, ethics-clearance claims, or another member's contribution.

---

## Part 5 — Co-Author Cheat Sheet

Every member must know these cold — expect any panelist to test any of the five:

1. **FLAIRE = Flood Level AI Risk Evaluation**; deployed in Brgy. Elvita, Narra, Palawan.
2. **Offline-first means:** classification, dashboard, and storage run on a Raspberry Pi at the barangay; internet only refreshes cached forecasts.
3. **Four risk levels:** Receding → Alert → Alarm → Critical; 20 fuzzy rules (15 core + 5 gap-fill).
4. **Two AI layers:** Random Forest (8 features → flood propensity) feeding a fuzzy-logic classifier (propensity + water level + rate of rise + forecast rain + tide → risk level).
5. **The honest numbers:** 94.26% = agreement with our own labeling rule, NOT flood prediction. 2 of 4 documented floods scored High — and both were the events our own rule already flags. 13,568 records / ~21.5 hours deployed. n=2 acceptability (5.00 five dimensions, 4.75 usability). Cost ₱23,700.
6. **SMS:** works, enabled on the device, triggers only at Alarm/Critical — never fired in the field because the river stayed at Receding.
7. **Three red lines:** never claim flood prediction, never claim lead time, never claim SMS was field-tested.
8. **The AI rationale in one breath:** "We added the AI layer to explore whether ML can help assess flood risk — Chapter 1 states it as an aim, Chapter 5 answers it: technically feasible, predictive value not yet established."

---

## Part 6 — Preparation Checklist & Fallback Strategy

### Must be true before the defense (document side)
- [ ] **Title-page date fixed** (Jan 2026 vs Oct 2026 deployment) — the #1 question, and the only one that must be *eliminated*, not answered.
- [x] **Chapter 2 residue (P281) — DONE in stage 11.** Reframed to "…the existing threshold-based warning infrastructure that the system developed in this study is designed to **complement rather than replace**." This was the written form of the deleted RQ3 comparison. The same pass also cleared "proposed"/future-tense residue at **P279, P280, P300** (Ch2), **P348, P476, P480** (Ch3), and the "Machine Learning model" naming at **P467**.
- [ ] **References inserted AND all in-text citation years filled** (Chapter 2 has ~15 blank slots — "The GSMA␣␣report", "Budimir et al.␣␣present", …). A reference list alone fixes neither.
- [ ] Appendices A/B/D–G, Acknowledgement, Gantt bars, TOC filled; all five bionotes/CVs present.
- [ ] Appendix C checked against the real administered questionnaire.
- [ ] List of Tables page numbers; MDRRMC/MDRRMO harmonized (MDRRMO is the municipal office; MDRRMC the council).

### Must be true before the defense (people side)
- [ ] **Each member's contribution agreed and truthful** — G1 cannot be improvised by five people separately.
- [ ] **P448 pilot-test answer:** recall who the instrument was piloted on (or how it was pre-checked) — with n=2, "pilot-tested" invites "piloted on whom?"
- [ ] **Ethics/clearance answer confirmed with your adviser.**
- [ ] **Authorship delta agreed:** the proposal listed one author, the thesis lists five. Agree one truthful sentence for "why five, and what did each of you do" and have all five use it — do not improvise it separately (H8, G1).
- [ ] **Title/acronym "AI" tension decided:** the thesis title omits "AI" while FLAIRE still expands to "Flood Level **AI** Risk Evaluation" and the abstract says "artificial-intelligence pipeline" (H7). Pick one line and hold it.
- [ ] **Sensor node transmission interval confirmed** against the deployed firmware — Chapter 3 says every 5 seconds, the proposal said every 10 minutes (H10). Do not answer this from memory.
- [ ] Open the deployed unit's config to have SMS evidence ready.
- [ ] Rehearse Part 2 aloud, twice — out loud, not read.

### When you get a question you can't answer
1. **Don't guess.** Say: *"That wasn't measured in this study"* or *"That's outside the scope as defined in Chapter 3 — but our recommendations address it at [topic]."*
2. **Bridge to the text:** *"The thesis addresses this in [chapter]…"* — even a partial anchor beats silence.
3. **Accept valid criticism outright:** *"You're right — that's listed among our limitations and the corresponding recommendation."* Panels reward honesty and penalize defense-of-the-indefensible far more than they penalize limitations.
4. **Defer gracefully:** *"That's a fair point we'd address in the next revision — noted."*
