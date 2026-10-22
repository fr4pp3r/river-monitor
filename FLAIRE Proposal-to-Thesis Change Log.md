# FLAIRE — Change Log: Approved Proposal → Revised Thesis

**Compared documents**

| | Document | Scale |
|---|---|---|
| Baseline | `FLAIRE-proposal-accepted.docx` | 594 paragraphs, 6 tables |
| Current | `FLAIRE Thesis 2 - 1 (Revised).docx` | 828 paragraphs, 13 tables |

**Method.** Full text and every table of both files were extracted in document order and compared chapter by chapter. All citations below are paragraph indices from that extraction (`P###`), which are identical to the numbering used in the working analysis files. Prose-only wording edits are grouped; anything that changes a promise, a number, a scope boundary, a method, or an identity (names, titles) is listed individually.

**How to use this.** §9 and §11 are the defense-critical parts: §9 lists every proposal commitment the thesis does not deliver, and §11 lists the questions the panel is most likely to ask because of those gaps, with a defensible one-line answer for each.

---

## 1. Bottom line

The thesis is a **narrowed and much more honest version** of the proposal. The architecture promised in the proposal was largely built, but three classes of change happened:

1. **Scope contracted.** Two sensor nodes became one; a monsoon-season data campaign became a short pilot deployment; respondents went from three stakeholder groups to two BDRRMC focal persons.
2. **Evaluation redefined.** The proposal promised a comparison against a traditional threshold-based method measured with accuracy, precision, recall, F1-score, **false alarm rate**, and **lead time**. The thesis drops the comparison entirely (declared future work) and reports only accuracy, precision, recall, F1 — reframed as a *consistency* check against rule-derived labels rather than validation against real floods.
3. **Framing made explicit.** Where the proposal asserted an "AI-enhanced predictive lead time" and a "24–48-hour predictive decision window", the thesis states plainly that lead time was not measured, the threshold baseline was out of scope, and the system is a decision-support tool, not an autonomous warning authority.

None of these are fatal, and the thesis documents each one itself — which is the correct defense posture. The risk is **not** the gaps; it is being surprised by them. Read §9 and §11.

---

## 2. Material deviations at a glance

| # | Item | Proposal | Thesis |
|---|---|---|---|
| 1 | Title | "FLAIRE: **AI** Offline-First Flood Early Warning System…" (P0) | "FLAIRE: Offline-First Flood Early Warning System…" (P0) |
| 2 | Authors | 1 — Betita, Nathaniel S. (P36, P47) | 5 — Betita, Cabotaje, Gabo, Hamad, Unos (P34–P38, P47) |
| 3 | Document type | "An Undergraduate Thesis **Proposal**" (P8) | "An Undergraduate Thesis" (P8) |
| 4 | Research questions | 4 (proposal RQ3 = compare vs threshold method) | 5 (comparison RQ deleted; new field-deployment RQ) |
| 5 | Sensor nodes | "two LoRa-based sensor nodes" (P235, P338, P378) | "a LoRa-based hydrological sensor node" — single unit (P247, P252, P349) |
| 6 | Predictive window | "24–48-hour predictive decision window" (P214, P223, P229, P235, P405) | removed; "cached forecasts up to seven days ahead" (P223, P313) |
| 7 | Threshold comparison | promised, with metrics (P225, P334, P380, P406) | "was not completed and is identified as future work" (P344, P250) |
| 8 | False alarm rate / lead time | promised evaluation metrics (P230, P237, P333, P380) | dropped; explicitly out of scope (P250) |
| 9 | Respondents | BDRRMC personnel + barangay officials + flood-affected residents (P237, P373) | BDRRMC focal persons only, n = 2 (P236, P251, P433, P447) |
| 10 | Data campaign | "collected during the 2026 monsoon season" (P235) | limited pilot field deployment only (P344, P540ff.) |
| 11 | Hardware | 2 × ESP32 nodes + ultrasonic, Raspberry Pi gateway (P378) | 1 × Adafruit 32u4 RFM9x node + ultrasonic + **rain gauge**, Raspberry Pi 5 (P366, P437) |
| 12 | Forecast source | OpenWeatherMap API (P379) | Open-Meteo API (P221, P343, P404) |
| 13 | Dashboard stack | Flask (P379, P402) | FastAPI (P467) |
| 14 | Total cost | ₱28,200 (total row, Table 3.1) | ₱27,920 (Table 3.2) |
| 15 | Alert channels | multi-channel: sirens, queued SMS, social media (P214, P243ff.) | dashboard + SMS at Alarm/Critical; siren/social media are BDRRMC actions (P249, P377) |
| 16 | Chapters 4–5 | headings only (P418, P420, P421) | full results and conclusions written from scratch |

---

## 3. Front matter

- **Title — "AI" removed.** `FLAIRE: AI Offline-First…` (P0) → `FLAIRE: Offline-First…` (P0). *Note the tension this creates:* the acronym still expands to "Flood Level **AI** Risk Evaluation" (P107, P223) and the abstract still says "a two-stage artificial-intelligence pipeline" (P108). See §10, item 1 — decide this before the defense.
- **Document type.** "An Undergraduate Thesis Proposal" (P8) → "An Undergraduate Thesis" (P8).
- **Authorship — 1 → 5.** Proposal title page lists only `Betita, Nathaniel S.` (P36) and the approval sheet names only him (P47, P49). Thesis lists Betita, Cabotaje, Gabo, Hamad, Unos (P34–P38) and the approval sheet names all five (P47). **This is the single largest identity change in the document.**
- **Abstract — written from nothing.** Proposal: "Abstract" heading (P106) followed only by the citation line (P107) — no abstract text. Thesis: full two-paragraph abstract (P108) plus `Keywords:` line (P109). The thesis abstract already contains the honest limitation — "classified two as High and two as Medium, indicating that the rule-derived training labels capture the strongest accumulated-rainfall signals but do not reliably encode flood occurrence."
- **Acknowledgement.** Heading only in both (proposal P73, thesis P73). Unchanged/empty.
- **Table of Contents.** Heading only in both. Unchanged/empty.
- **List of Tables — expanded 1 → 8.** Proposal: `Table 3.1 Cost Analysis` only (P162). Thesis: `Table 3.1 Fuzzy-logic decision rules`, `Table 3.2 Cost Analysis`, `Table 4.1`–`Table 4.6` (P164–P171). Tables 4.1–4.6 carry no page numbers.
- **List of Figures — inherited unchanged.** Same seven entries in both (proposal P184–P190; thesis P193–P199): Figures 2.1, 3.1, 3.2, 3.3.1–3.3.3, 3.4. Only change: Figure 3.3.1 caption singularised — "hydrological sensor **nodes** flowchart" → "hydrological sensor **node** flowchart" (P187 vs P196).
- **List of Abbreviations.** Carried over from the proposal essentially intact; the proposal's `BT | Bluetooth` entry is removed in the thesis. The rest — including entries not used in the thesis (DIMER, CSU-MLP, HEC-HMS, SOM, SVM, LSTM, GRU, WRF, KoICA, EW4A, NRMSE, NSE, PBIAS) — is inherited from the proposal's broader literature review.

---

## 4. Chapter 1 — Introduction

### Background of the Study

- **Softened opening.** "flooding **poses** a persistent threat" (P209) → "flooding **remains** a persistent threat" (P218).
- **Citation added to the site justification.** Thesis adds `(Radyo Natin Nationwide, 2020)` to the provincial FEWS pilot-site sentence (P219); the proposal had the same statement uncited (P210).
- **"flash floods" → "flooding".** P210 → P219. Consistent with the Scope statement that upstream flash flooding is excluded (P245).
- **A claim about the existing FEWS was deleted.** Proposal: "Despite these efforts, the system's reactive nature, dependent on real-time thresholds and online access, limits predictive lead time during network outages common in typhoons." (P210) — not present in the thesis's parallel paragraph (P219). Removes an unverifiable assertion about the installed provincial system.
- **Threshold-limitation list broadened.** Added "tide conditions" to the factors traditional systems ignore (P211 → P220).
- **Key reframing — "AI-based flood risk classification" removed from the rationale.** Proposal: "This underscores the need for offline predictive enhancements **such as AI-based flood risk classification**, supported by local hydrological data…" (P211) → Thesis: "These limitations underscore the need for **offline predictive decision-support tools that can use local hydrological and meteorological data** even when internet connectivity is unavailable." (P220)
- **Forecast inputs changed.** "Cached weather forecast data, pre-downloaded **daily**… rainfall predictions, **atmospheric pressure, humidity, and precipitation probability**" (P212) → "Cached **weather and tide** forecast data, pre-downloaded **at least daily (every six hours)**… through services such as **OpenMeteo**… rainfall predictions, **temperature extremes, and tide levels**" (P221). Also adds rainfall to the sensor payload and adds fuzzy logic to the local-compute sentence.
- **Comparative gap claim removed.** Proposal: "limited empirical research at the barangay scale that systematically evaluates **and compares offline AI-based flood risk classification systems with traditional threshold-based warning methods** in the Philippine context." (P213) → Thesis: "limited empirical research at the barangay scale that systematically evaluates **such hybrid AI-based flood-risk classification systems** in the Philippine context." (P222) **This is the prose counterpart of the deleted RQ3** — the thesis stopped claiming it would do a threshold comparison in the literature-gap argument as well as in the method.
- **System description rewritten to what was built.** Proposal (P214): "collect real-time water level measurements from **2 LoRa-based hydrological sensors**… via LoRa (primary) and **SMS fallback for redundancy**… a **Machine Learning classification model**… cached **7-day** weather forecasts… providing a **24–48-hour predictive decision window**… Personnel will make the final call to activate **sirens, queued SMS, or social media alerts**, ensuring human oversight while benefiting from **AI-enhanced predictive lead time** over purely reactive threshold-based methods… historical meteorological data from **PAGASA**, local flood records, and real-time sensor data." → Thesis (P223): "collects real-time water-level measurements **and rainfall amount** from **a LoRa-based hydrological sensor node**… to a **Raspberry Pi 5** edge device… the **Random Forest model** analyzes… **R1, R3, R7, rainy_days, TMAX, TMIN, TideMax, and TideMin**… the **fuzzy-logic classifier**… **four flood-risk levels**… drawing on **cached forecasts up to seven days ahead**." No 24–48 h window, no SMS fallback, no lead-time claim.
- **New aim sentence added.** Thesis P224 adds: "…and to explore whether **machine-learning models can be used to assist in assessing flood risk at the barangay scale**."
- **Locale style.** "in the **municipality** of Narra" (P210) → "in the **Municipality** of Narra" (P219).

### Statement of the Problem — 4 RQs → 5 RQs

| | Proposal | Thesis |
|---|---|---|
| RQ1 | key problems and limitations, and how they can be addressed by an AI-based system | same question, reframed to an "offline-first, AI-based flood early-warning system" (P228) |
| RQ2 | how the system "can be designed and developed… integrating:" cached weather data (P221), sensor data, an ML model within a 24–48-hour window (P223), a dashboard (P224) | how the system "can be designed and developed… integrating:" cached seven-day weather and tide data from OpenMeteo (P230), real-time water-level and rainfall data from a LoRa node → Raspberry Pi 5 (P231), the hybrid Random Forest + 20-rule fuzzy pipeline (P232), dashboard and SMS alerts (P233) |
| RQ3 | "How does the AI-based flood risk classification model **compare with a traditional threshold-based warning method** using confusion matrix analysis and performance metrics such as accuracy, precision, recall, F1-score, **false alarm rate, and lead time**?" (P225) | **DELETED.** Replaced by: "How **consistently** does the Random Forest flood-propensity model **reproduce the rule-derived** Low, Medium, and High categories on a held-out test set, in terms of accuracy, precision, recall, and F1-score?" (P234) |
| RQ4 | — | **NEW:** "How did the FLAIRE prototype perform during a **limited field deployment** in terms of sensor-data capture, data logging, and data quality?" (P235) |
| RQ5 | "How acceptable… to **target users and stakeholders** in terms of functionality, usability, reliability, and perceived **improvement** in disaster preparedness?" (P226) | "How acceptable… to the **BDRRMC focal persons** of Brgy. Elvita… in terms of functionality, usability, reliability, perceived **contribution to** disaster preparedness, **attitude toward use, and intention to use**, as measured through a **Technology Acceptance Model (TAM)-based** interview or survey?" (P236) |

**Read RQ3 carefully before the defense.** The proposal's third question is the one a panelist is most likely to remember. Its replacement is not a minor rewording: it changes *validity against reality* into *internal consistency with a rule*. The thesis says this openly (P250, P603) — say it openly too.

### Significance of the Study

- Tense converted to what was actually done; the education/policy significance paragraph is broadly retained with new framing (P239–P242).
- **The 24–48-hour window claim is gone** from the practical-significance paragraph (P229 → P239).
- **The academic-significance claim is gone.** Proposal: "will contribute empirical evidence at the barangay level by **evaluating an AI-based flood risk classification model against traditional threshold-based methods**… using metrics such as accuracy, precision, recall, F1-score, **false alarm rate, and lead time**." (P230) → Thesis (P241) instead frames the contribution as "a documented, reproducible implementation… **together with an honest account of its limitations**", and states the Random Forest "was evaluated for **consistency with a rule-derived scoring scheme rather than validated against independent flood events**".
- **New hybrid-design paragraph.** P240 explains the Random Forest + fuzzy-logic division of labour and states the system "functions as a **decision-support tool rather than a replacement for human judgment**".
- **New limitation-aware paragraph.** P242: "While the pilot deployment was **limited in duration and local conditions**, its findings can serve as an initial basis for refining FLAIRE".

### Scope and Delimitations

- Proposal: "Real-time data **will be collected during the 2026 monsoon season** using **two LoRa-based sensor nodes** equipped with ultrasonic water level sensors." (P235) → Thesis: "Real-time hydrological data **were collected using a LoRa-based sensor node** equipped with an ultrasonic water-level sensor **and a rain gauge**." (P247) — one node, rain gauge added, monsoon campaign dropped.
- Proposal: the model "**will be compared with traditional threshold-based warning methods**" (P236) → **removed**; thesis states the opposite (P250): "**measurement of forecast lead time and comparison with a threshold-based baseline were outside the scope of this study and are identified as future work.**"
- Proposal evaluation clause: "multi-class confusion matrix analysis and quantitative metrics such as accuracy, precision, recall, F1-score, **false alarm rate, and lead time**, along with qualitative feedback from **BDRRMC staff, barangay officials, and selected residents**." (P237) → Thesis (P250–P251): confusion matrix + per-class metrics; fuzzy layer "verified functionally by sweeping its five input variables"; "limited field deployment to assess sensor-data capture, data logging, and data quality"; "preliminary four-event case check (Table 4.4)"; feedback from BDRRMC focal persons only.
- **Data sources expanded.** Thesis adds NAMRIA (tide) alongside PAGASA, and Open-Meteo for forecasts (P246).
- **Alert dissemination clarified.** "supported SMS notifications… **each alert is logged locally**… sent through a GSM modem when it is reachable. **Final public alert dissemination, including siren activation and social-media posting, remained under the authority of the BDRRMC.**" (P249)
- **New explicit limitation.** "This study is limited to a prototype deployment using a **single sensor node** and does not provide full river-system coverage." (P252)

### Definition of Terms

- **Confusion Matrix redefined honestly:** "against **actual outcomes**" (P245) → "against the **reference labels**" (P258).
- **Hydrological Sensors expanded:** "measure real-time water levels using ultrasonic sensing" (P249) → "…**and rainfall amount using rain gauge**" (P262).
- **False Alarm Rate retained as a defined term** (P260) even though the metric is no longer evaluated — a defined-but-unused term the panel could notice.
- The proposal's multi-channel alert definitions ("Queued SMS", "Multi-Channel Alert Dissemination") are gone, replaced by prototype-scoped SMS-alert wording with store-and-forward as future work.

---

## 5. Chapter 2 — Theoretical Framework

- **Structure unchanged.** Same four sections in both: Review of Related Literature (Local / Foreign), Conceptual Framework, Research Paradigm.
- **Literature is carried over, not replaced.** The same source set appears in both versions: NDRRMP 2020–2030, KOICA–DOST/PAGASA EWS4 (P268/P280), Radyo Natin Nationwide (P269/P281), GSMA, ITU/Gray, Budimir et al., Semtech, Cacal/Austria/Taboada, Macalalad et al., Mesias & Bagtasa, Ahmed, Schumacher et al. (CSU-MLP), Sehgal et al., Refadah. **No substantially new literature was added for the Random Forest or fuzzy-logic choice** — the sources that support Random Forest (Mesias & Bagtasa, Schumacher et al., Refadah) were already in the proposal. There is no equivalent literature support introduced for the fuzzy-logic layer.
- **Tense/voice conversions throughout.** e.g. "These findings reinforce the importance of designing the **proposed** system…" (P275) → "…designing **this study's** system…" (P287); "supports Random Forest as a viable classification algorithm option for the **proposed** flood risk classification system" (P290) → "…for the **developed** flood risk classification system" (P302). Parallel edits recur at P288/P300, P292/P304, P293/P305, P294/P306, P295/P307.
- **Residual "proposed" wording — inconsistent with completion.** P281 still ends: "…documents the existing threshold-based warning infrastructure that the **proposed** AI-enhanced hybrid system aims to augment and improve upon." This both keeps the proposal's tense *and* reasserts that the system augments a threshold-based method — which §1/§6 of the thesis elsewhere declines to compare against. Flag for a copy fix.
- **Blank in-text citation years (unfilled placeholders).** Roughly fifteen sites between P282 and P308 have had their year removed, leaving a double space: "The GSMA  report" (P282), "Gray  of the International Telecommunication Union" (P286), "Budimir et al.  present" (P287), "Semtech  provides" (P288), "Macalalad et al.  addressed" (P300), "Ahmed  designed" (P304), "Schumacher et al.  document" (P305), "Sehgal, Gurudiwan, and Pant  proposed" (P306), "Refadah  presents" (P307), "Cacal, Austria, and Taboada  conducted" (P298). Parenthetical years survive elsewhere (e.g. "(2021)", "(2023)", "(2025)"), so the citation state is internally inconsistent — almost certainly a bibliography-in-progress artifact and evidence the reference list is still being assembled.
- **Conceptual Framework — inputs changed.**
  - Proposal (P300): inputs = (1) cached weather forecast data from public APIs — rainfall, precipitation probability, humidity, atmospheric pressure, updated daily; (2) real-time hydrological data from **two** LoRa sensor nodes; (3) historical reference data from meteorological records and local flood occurrence data.
  - Thesis (P312): (1) cached **seven-day weather and tide** data from **Open-Meteo**, updated **at least daily (every six hours)**, covering rainfall-related variables, **temperature extremes, and tide levels**, stored in SQLite; (2) real-time data from **a** LoRa sensor node with **ultrasonic water-level sensor and rain gauge** → **Raspberry Pi 5**; (3) historical **meteorological and tide** records and local flood-occurrence information.
- **Conceptual Framework — process made explicit.**
  - Proposal: generic hybrid AI-based system (P301ff.).
  - Thesis (P313): two stages named — Random Forest using `R1, R3, R7, rainy_days, TMAX, TMIN, TideMax, TideMin`, then a **20-rule fuzzy classifier (15-rule core + 5 gap-fill)** fusing propensity with water level, rate of rise, forecast rainfall, and tide level → four levels (Receding, Alert, Alarm, Critical). Ends with the key substitution: "Together, these processes use the **cached seven-day forecast horizon as the available decision window**" — this replaces the proposal's 24–48-hour window claim.
- **Conceptual Framework — output reframed.** New thesis sentence (P315): "The system will function as a **decision-support tool rather than an autonomous warning authority**".
- **Research Paradigm.** Only tense: "This study **will follow** a developmental and evaluative research paradigm…" (P306) → "This study **followed**…" (P319).
- **Framework naming.** Proposal: "hybrid AI-based flood risk prediction and early warning system" (P306) → Thesis: "hybrid **Fuzzy-AI riverine flood-risk classification and** early-warning system" (P311); FLAIRE expansion "Flood Level AI Risk Evaluation" now spelled out in Ch2 (P311).

---

## 6. Chapter 3 — Research Methodology

### Research Design

- **DRM phase names rewritten.** Proposal (P322): phases adapted into "**planning and design, system development, field testing, and evaluation**". Thesis (P331): "**planning and requirements analysis, system design and development, pilot deployment and field testing, and evaluation and refinement**".
- **Citation dropped.** Proposal attributed the framework to "the four-phase Design Research Methodology (DRM) framework **proposed by Blessing and Chakrabarti (2009)**" (P322). The thesis's opening sentence (P331) no longer carries that attribution. With the reference list still empty, restoring this attribution is cheap and closes a reviewer question.
- **What is refined changed.** "iterative refinement of the system, including the **Machine Learning model**, dataset preprocessing, and overall architecture" (P332) → "iterative refinement of the **Random Forest model, fuzzy-logic rules**, dataset preprocessing, system architecture, **and user interface**" (P341).
- **Metrics promise cut.** Proposal (P333): performance "evaluated using standard machine learning metrics such as accuracy, precision, recall, F1-score, **false alarm rate, and lead time**." → Thesis (P345): "quantitative performance metrics, including **accuracy, precision, recall, and F1-score**."
- **Whole comparison paragraph deleted.** Proposal (P334): "The Machine Learning flood risk classification model **will be compared with a traditional threshold-based warning method using the same dataset and evaluation metrics** to ensure consistency…" → Thesis (P344): "…comparison with a traditional threshold-based warning method **was not completed and is identified as future work**."
- **Phase 3 rewritten around the pilot.** Thesis (P344) adds: "During the field test, real-time sensor data and system-generated risk classifications were recorded simultaneously."
- **Phase 4 expanded to six acceptability dimensions.** Proposal: acceptability, functionality, usability, reliability, perceived contribution (P372, P377) → Thesis (P345): adds "**attitude toward use, and intention to use**", gathered "from BDRRMC focal persons using a TAM-based survey instrument".

### Locale of the Study

- Site sentence identical except anchor (P337 → P348), including the retained `(Radyo Natin Nationwide, 2020)`.
- **Present-tense residue.** "The barangay **is selected** due to its documented exposure…" (P348) survives into the completed thesis — the surrounding chapter is past tense (P331, P342–P345). Consistency fix.
- **Placement made specific:** proposal "will be installed along a **selected river section**" (P338) → thesis "was installed on **Purok 1 of Brgy. Elvita, the lowest area near the river section, where residents settled**" (P349).

### System Architecture — **NEW SECTION** (thesis P366–P377)

Not present in the proposal. Adds five explicitly named layers:

| Layer | Thesis content | Para |
|---|---|---|
| Sensor | Adafruit 32u4 RFM9x LoRa node, ultrasonic water-level sensor **+ rain gauge** | P366 |
| Communication | LoRa primary link, no internet required; readings stored locally on receipt | P368 |
| Processing / edge | Raspberry Pi 5; Random Forest on the eight named features → 20-rule fuzzy (15 core + 5 gap-fill) → Receding / Alert / Alarm / Critical | P371 |
| User interface | LAN web dashboard on the Raspberry Pi 5 (real-time readings, cached forecast, AI classifications, trends, system status) | P376 |
| Alert dissemination | SMS auto-sent to pre-configured BDRRMC numbers on **Alarm or Critical**, logged locally; BDRRMC decides on resident warning, **siren activation and social-media posting** | P377 |

### Flowchart of the Proposed System → Flowchart of the Developed System

- Section renamed from "proposed" to "developed".
- **Sensor transmission interval changed by 120×:** proposal "transmit it to the edge device for processing **every 10 minutes**" (P359) → thesis "…**every 5 seconds**" (P389). Reconcile this against the system's actual LoRa duty cycle and database volume before the panel finds it — 5-second intervals and 10-minute intervals imply very different power budgets and record counts.
- **Edge device description upgraded.** "threshold logic and a **Machine Learning classifier**" (P364) → "threshold logic and a **Random Forest + fuzzy-logic flood risk classification system**" (P394).
- **Dashboard flowchart (3.3.3) unchanged** in substance (P370 → P400).

### Data Collection and Preprocessing — **NEW SECTION** (thesis P403–P428)

Not present in the proposal at all. Contents:

- Four data streams: historical, forecast, real-time, field observation (P403).
- Historical meteorology from **PAGASA**, historical tide from **NAMRIA**, forecasts from **Open-Meteo** (P404) — NAMRIA and Open-Meteo are new relative to the proposal, which named only PAGASA and BDRRMC local records.
- Real-time capture: LoRa node with ultrasonic sensor **and rain gauge** → Raspberry Pi 5 → validation → SQLite (P414–P415).
- **New justification for the missing baseline (P416):** "Although a provincial Flood Early Warning System was previously installed in Brgy. Elvita, it was **not operational, standardized, or formally documented during the study**; therefore the study did not treat a local threshold-based method as an established ground-truth baseline. Instead, the observed flood-risk condition… was established using a combination of **manual water-level readings, visual observations of the river, recorded weather conditions, and available information from the Municipal Disaster Risk Reduction and Management Office (MDRRMC)**."
- Input preparation for Random Forest (eight features) and for fuzzy logic (five inputs) (P425–P426).
- Dataset partitioning (P427) and local SQLite storage (P428).

### Target Respondents

- **Respondent base cut from three groups to one.**
  - Proposal (P373): "BDRRMC personnel…; **barangay officials** responsible for local disaster coordination; and **selected community representatives from flood-affected households** as secondary stakeholders providing feedback."
  - Thesis (P431–P433): "BDRRMC focal persons" only; adds an explicit generalizability caveat — "the findings should be interpreted as **preliminary feedback from key local disaster-risk personnel rather than as a generalizable measure of system acceptability for the entire barangay**."
- The evaluation dimensions were widened to six (P432) even as the respondent pool narrowed to two.

### Instrumentation

- **Hardware changed.**
  - Proposal (P378): "**two** LoRa-based sensor nodes equipped with ultrasonic water level sensors integrated with **ESP32 microcontrollers**. A Raspberry Pi-based gateway…" → Thesis (P437): "**a** LoRa-based hydrological sensor node… **Adafruit 32u4 RFM9x LoRa microcontroller**, an ultrasonic water-level sensor, **and a rain gauge**… **Raspberry Pi 5**."
- **Software stack changed.**
  - Proposal (P379): "cached weather data pipeline… **OpenWeatherMap API**… Machine Learning classification model implemented using the **scikit-learn** library… **Flask**-based LAN web dashboard… **GSM modem will be used to support queued SMS alert delivery**."
  - Thesis (P438, P467): cached **Open-Meteo** weather **and tide** forecasts; Random Forest + fuzzy-logic pipeline; **FastAPI** LAN dashboard; SMS notifications via GSM modem. "Queued" is dropped from the SMS description in the instrumentation narrative (the store-and-forward idea survives only as future work).
- **New reference-data instrument.** Because no threshold system was operational, the thesis adds a **field observation form** plus manual water-level readings as the reference for the field-test comparison (P439).
- **TAM instrument retained but respondent count is tiny.** Five-point Likert scale, 1 = Strongly Disagree to 5 = Strongly Agree (P447); "reviewed and validated by subject-matter experts… also **pilot-tested** before formal administration" (P448). With n = 2, "pilot-tested" reads strained — expect a question about who it was piloted on.
- **Metrics paragraph trimmed.** Proposal (P380) promised confusion matrix **plus** false alarm rate, lead time, **and** comparison with a threshold-based method "using the same dataset to ensure a consistent and fair evaluation" → all three removed in the thesis.

### Gantt Chart

- Section present in both (proposal P382, thesis P450) and still listed as Figure 3.4 in both figure lists. **The grid itself remains unfilled in the thesis** while the surrounding narrative (P460) describes the schedule — the narrative and the empty chart contradict each other on the page. Listed among the still-open items in §10.

### Cost and Benefits Analysis

- **Table renumbered and rewired.** Proposal Table 3.1 → thesis Table 3.2 (Table 3.1 is now the fuzzy-logic rule table).

| Row | Proposal (₱) | Thesis (₱) |
|---|---|---|
| Board | WiFi LoRa 32 V4 ESP32 BT development board x3 — 5,400 | Adafruit 32u4 RFM9x LoRa development board x3 — 5,400 |
| Edge computer | Raspberry Pi AI HAT+ 2 — **9,000** | Raspberry Pi 5 — **6,500** |
| Water-level sensor | Ultrasonic Water Level Sensor **x2** — 800 | Ultrasonic Water Level Sensor — 800 |
| Enclosure | Enclosure / Weatherproof Housing **x2** — 2,000 | Enclosure / Weatherproof Housing — 2,000 |
| Power | Power Supply / Solar Panel Kit **x2** — 3,000 | Power Supply / Solar Panel Kit — 3,000 |
| Miscellaneous | Miscellaneous Hardware — 2,000 | Miscellaneous Hardware — 2,000 |
| Weather API | **Weather Forecast API — 2,000** | **row removed** |
| SMS | SMS Gateway Service (yearly) — 2,000 | GSM modem SIM and SMS load (yearly) — 2,000 |
| Transport | Transportation and field deployment — 1,000 | Transportation and field deployment — 1,000 |
| Printing | Printing, documentation, and miscellaneous — 1,000 | Printing, documentation, and miscellaneous — 1,000 |
| **Total** | **₱28,200** | **₱27,920** |

  Net: −₱2,500 on the edge computer (Pi AI HAT+ → Pi 5), −₱2,000 by deleting the paid Weather Forecast API (Open-Meteo is free), and the per-node "x2" quantities dropped for the single-node build. The ₱800 ultrasonic sensor line and the ₱5,400 board line still reflect multi-unit purchases. Note: the thesis column above records the earlier comparison; Table 3.2 has since been revised to the actual-parts BOM (25 line items — Node ₱7,070, Edge ₱19,050, General ₱1,800 — totaling ₱27,920), which is why the thesis rows no longer sum to the total row.
- **Narrative changed.** "deployment of **2 sensor nodes**" (P398) removed (P463); "ESP32 LoRa V3 boards… **Raspberry Pi 4**… **Flask** LAN dashboard… **IP67 enclosures**… approximately **₱9,400 per sensor node**" (P402) → "**Adafruit 32u4 RFM9x LoRa boards**… **Raspberry Pi 5**… **FastAPI** LAN dashboard… **weather-resistant enclosures**" (P467); the per-node ₱9,400 figure and the IP67 rating are gone. Note P467 still says "**Machine Learning model**" where the rest of the thesis says Random Forest + fuzzy logic — a naming inconsistency.
- **Benefits rewritten.**
  - Proposal (P405): "support a **24–48-hour predictive decision window** through local AI analysis of cached weather data and real-time LoRa sensor inputs" → Thesis (P470–P471): continuous monitoring, local storage, Random Forest + fuzzy-logic pipeline on the Raspberry Pi 5, LAN dashboard; "the system is **designed to** generate Alert, Alarm, or Critical classifications and to send SMS notifications for Alarm or Critical conditions."
  - Proposal (P406): "support **empirical comparison between a Machine Learning classification model and a threshold-based warning method using standard evaluation metrics**" → **removed**; replaced by the decision-support framing (P472): "the system functions as a **decision-support tool rather than an autonomous warning system**."

### System Maintenance Plan

- Modality softened: proposal "Routine monitoring **will be** conducted… Periodic on-site inspections **will be** performed" (P410) → thesis "Routine monitoring **can be** conducted… Periodic on-site inspections **should be** performed" (P474).
- Monitoring scope trimmed: "sensor uptime, **signal strength, battery levels**, database status, and model performance" (P410) → "sensor uptime, database status, and model performance" (P474).

### Developer and Client Communication

- Tense only: "A structured communication plan **is proposed**… This **will include**" (P415) → "…**is planned**… This **includes**" (P479).

---

## 7. Chapters 4 and 5 — written from nothing

**Proposal state:** "RESULTS AND DISCUSSION" (P418) — heading only; "Chapter 5" (P420); "SUMMARY OF FINDINGS, CONCLUSIONS, AND RECOMMENDATIONS" (P421) — heading only. Both chapters were empty placeholders.

**Thesis Chapter 4** now contains seven sections:

| Section | Para |
|---|---|
| Current Flood Warning Practices in Brgy. Elvita | P486 |
| Development and Implementation of FLAIRE | P498 |
| Random Forest Model Evaluation Results | P511 |
| Fuzzy-Logic Coverage and Functional Verification | P527 |
| Preliminary Check Against Documented Flood Events | P533 |
| Limited Field Deployment Results | P540 |
| Initial Acceptability Results | P563 |

**Thesis Chapter 5** now contains three sections: Summary of Findings (P579), Conclusions (P598), Recommendations (P612).

**Headline content added (all new relative to the proposal):**

- **Training data.** 1,826 daily records, 2 January 2020 – 31 December 2024; meteorological from **PAGASA**, tidal from **NAMRIA**; stratified 80/20 split → 1,460 train / 366 test (P512).
- **Random Forest performance** (P521–P522, Table 4.2): overall test accuracy **94.26%** (345/366). Per class — Low P/R/F1 = 0.9728/0.9728/0.9728 (n=184); Medium 0.9298/0.8908/0.9099 (n=119); High 0.8824/0.9524/0.9160 (n=63). Macro average F1 0.9329; **weighted average 0.9433 / 0.9426 / 0.9426**. High recall 0.9524 (60 of 63); High precision 0.8824 because **eight Medium-labeled samples were classified as High**; no High-labeled samples were classified as Low.
- **Critical framing sentence (P603):** "…because the Low, Medium, and High labels were derived from the same input features, the result demonstrates **consistency with the predefined scoring rule rather than independent flood-prediction performance**."
- **Fuzzy-logic verification** (P527–P530): five inputs swept — water level (0–3000 mm), rate of rise (−100 to 100 mm/h), forecast rainfall (0–100 mm/day), tide level (0–5 m), Random Forest propensity (Low/Medium/High). **768 dominant-term combinations** (4×4×4×4×3) plus a **3,150-point grid**; **all** returned a defined class; all four risk classes reachable; output monotonic in water level and rate of rise; single boundary steps in the other three inputs. **296 of 768 (38.5%)** resolved by an explicitly identified rule; the rest by the membership-weighted fallback. Explicitly labelled "a **functional verification** of the fuzzy layer, **not evidence of accuracy against actual floods**" (P530).
- **Documented-flood-event check** (P533ff., Table 4.4): four documented events; the rule/Random Forest verdict is **2 High, 2 Medium**. (The abstract states this on P108 as evidence that the labels "capture the strongest accumulated-rainfall signals but do not reliably encode flood occurrence".)
- **Field deployment** (P540ff.): **13,568** LoRa-sourced deployment records; median water level **0.122 m**; recorded range **−0.012 m to 2.500 m** (P543).
- **Sensor data quality** (P590, Table 4.5): 67 records with zero raw ultrasonic distance and a corresponding 2.500 m water-level reading; **124 records with negative calculated water levels**; five records with implausibly short raw distances (250 mm and 959 mm) producing 2.250 m and 1.541 m. "**flagged for quality review rather than interpreted as actual river-level changes**."
- **Acceptability** (P563ff., Table 4.6): n = 2 BDRRMC focal persons. Functionality **5.00**, Usability **4.75**, Perceived reliability **5.00**, Perceived contribution to disaster preparedness **5.00**, Attitude toward use **5.00**, Intention to use **5.00** (P569, P593), with the caveat that these "should not be generalized to all barangay officials or residents."
- **Explicit non-claims in Chapter 5**: the deployment "produced only **low-water (Receding) conditions**", which is why the fuzzy layer was verified by input-space sweeping rather than observed flood behaviour (P528); lead time and the threshold baseline remain out of scope.

---

## 8. Back matter

- **References.** Proposal: "References" heading only (P423), no content. Thesis: "References" heading (P638) with the placeholder **`[Insert reference list here.]`** (P639). Still empty — and now the only thing standing between the document and a complete reference apparatus. ~15 in-text citations in Chapter 2 are also missing their years (§5).
- **Bionotes.** Both versions carry a bionote table for **Nathaniel S. Betita** (proposal P426, thesis P642) and for the adviser **Joel P. Gulane Jr.** (proposal P429, thesis P645). Adviser text was corrected: "**the current department** of the Computer Science program" → "**the current department head** of the Computer Science program".
  - **Gap created by the authorship change:** the four added co-authors (Cabotaje, Gabo, Hamad, Unos) appear on the title page and approval sheet but have **no bionotes**, and the thesis ends with a dangling "CURRICULUM VITAE" heading at P827 after Betita's. The proposal had no such gap because it had one author.
  - **Misspelling fixed.** The proposal's bionote table left cell read "**Betitta**, Nathaniel S." against a body that says "Betita" (the only occurrence of "Betitta" in either document is at prop P426); the thesis corrects it to "Betita".
  - **New duplication defect.** The thesis adviser bionote (P645) repeats the sentence "His commitment to education is evident in his passion for teaching, training, and his involvement in the technology and computer-related industries." **twice**; the proposal carried it once (P429).
- **Appendices.**
  - **Appendix C is the one substantive addition.** Proposal: "SURVEY QUESTIONAIRE" heading with no content. Thesis: heading corrected to "SURVEY **QUESTIONNAIRE**" and the full **24-item TAM instrument** is present (P718–P756).
  - Appendices **A, B, D, E, F** are still headings without content in the thesis — the same state as the proposal.
  - **Appendix G** contains only Betita's CV, as in the proposal.

---

## 9. Proposal commitments not delivered

This is the list to rehearse. Each row: what was promised, where, and what the thesis says instead.

| # | Commitment (proposal) | Where promised | Thesis position |
|---|---|---|---|
| 1 | Compare the model against **a traditional threshold-based warning method** | RQ3 (P225); method (P334); instrumentation (P380); benefits (P406) | Not done — "**was not completed and is identified as future work**" (P344); justified by the absence of an operational, standardized, documented local baseline (P416); Scope states the comparison was outside scope (P250) |
| 2 | Report **false alarm rate** | P230, P237, P333, P380 | Not reported anywhere; still defined as a term (P260) |
| 3 | Report **lead time** | P230, P237, P333, P380 | Not measured; out of scope (P250) |
| 4 | Provide a **24–48-hour predictive decision window** | P214, P223, P229, P235, P405 | Replaced by "cached forecasts up to seven days ahead" as the available decision window (P223, P313); no lead-time claim retained |
| 5 | Deploy **two** LoRa-based sensor nodes | P235, P300, P338, P378 | One node deployed (P247, P252, P349); the "x2" cost lines were dropped |
| 6 | Collect real-time data across the **2026 monsoon season** | P235 | Limited pilot field deployment only (P344, P540ff.) |
| 7 | Gather feedback from **BDRRMC staff, barangay officials, and selected residents** | P237, P373 | Two BDRRMC focal persons only (P236, P251, P433, P447) |
| 8 | Deliver **multi-channel** alerts: sirens, queued SMS, social media | P214; alert definitions | SMS at Alarm/Critical + LAN dashboard; siren and social media are BDRRMC actions, not system outputs (P249, P377) |
| 9 | **SMS fallback for sensor transmission redundancy** | P214 | Removed — the node transmits via LoRa to the edge device only |
| 10 | Justify the system by **AI-enhanced predictive lead time over purely reactive threshold-based methods** | P214, P229, P230 | Removed; replaced by decision-support framing and an explicit limitations account (P240, P250, P472) |

**Items 9 and 10 are the least likely to be asked about in isolation, but together with 1–4 they form the panel's most probable line of attack: "your proposal promised a comparative, lead-time-measured evaluation; your thesis delivers a consistency check."** The thesis already carries the answer — use it.

---

## 10. Residual defects this comparison exposes

Beyond the unfulfilled-commitment list, the cross-read surfaces these unresolved items:

1. **Title vs acronym vs abstract.** The title dropped "AI" (P0), but the acronym expands to "Flood Level **AI** Risk Evaluation" (P107, P223, P311) and the abstract calls the pipeline "two-stage **artificial-intelligence**" (P108). Decide one line and make it uniform: either the title keeps "AI", or the defense explains why the title is narrower than the system.
2. **Ch2 keeps "proposed" and the threshold framing.** P281 still says "the **proposed** AI-enhanced hybrid system aims to **augment and improve upon** [existing threshold-based] infrastructure."
3. **Ch3 present-tense residue.** "The barangay **is selected**…" (P348) in an otherwise past-tense chapter.
4. **Dropped attribution in Research Design.** "(Blessing and Chakrabarti, 2009)" (P322) is no longer present in the thesis's DRM sentence (P331).
5. **Transmission interval mismatch.** 10 minutes (proposal P359) → **5 seconds** (thesis P389). Confirm which the deployed node actually uses and that the power/duty-cycle story is consistent.
6. **Chapter naming inconsistency.** "Machine Learning model" at P467 vs "Random Forest + fuzzy-logic" everywhere else.
7. **Defined-but-unused terms.** False Alarm Rate (P260) and Lead Time remain in Definition of Terms though neither is evaluated.
8. **Citation placeholders.** ~15 blank in-text years in Ch2 (P282–P308); References still `[Insert reference list here.]` (P639).
9. **Container items still empty.** Table of Contents, Acknowledgement, Gantt grid (Figure 3.4 / Table 2), Appendices A/B/D–F, co-author bionotes, dangling "CURRICULUM VITAE" heading (P827).
10. **List of Tables.** Tables 4.1–4.6 have no page numbers; the List of Figures is inherited from the proposal unchanged (no new figures were added for the new Ch4 tables).
11. **Duplicated sentence in the adviser bionote.** The thesis repeats "His commitment to education is evident in his passion for teaching, training, and his involvement in the technology and computer-related industries." twice at P645; the proposal had it once (P429).
12. ~~Cost rows still show multi-unit quantities~~ **Resolved** — Table 3.2 was revised to the actual-parts BOM (25 items grouped Node / Edge / General, totaling ₱27,920); no multi-unit rows remain.

**Fixed after this comparison was written** (stage 11, applied to the docx and verified — 828 paragraphs / 13 tables unchanged, no stale strings, run structure preserved): item **2** (P279, P280, P281, P300), item **3** (P348, plus future-tense residue at P476 and P480), and item **6** (P467). Items **1, 4, 5, 7–11** remain open; item **12** was resolved by the Table 3.2 cost revision.

---

## 11. Questions this delta invites — and the answers the thesis already supports

**Q1. Your proposal promised a comparison against a traditional threshold-based method, with false alarm rate and lead time. Where is it?**
The comparison was not completed and is identified as future work (P344). The justification is documented rather than asserted: the provincial FEWS previously installed in Brgy. Elvita was not operational, standardized, or formally documented during the study, so there was no defensible ground-truth baseline to compare against (P416). The thesis states explicitly that forecast lead time and the threshold baseline were outside scope (P250). *Do not claim the comparison was done, and do not describe it as a failure — it is a scoped-out item with a stated reason.*

**Q2. The third research question changed from "compare with a threshold method" to "reproduce the rule-derived labels". Isn't that moving the goalposts?**
Answer from the text, not around it: the labels the Random Forest predicts are generated from the same features the model uses, so the honest question is whether the model reproduces that scoring rule — and the thesis says so in the question itself (P234) and in the results: "**consistency with the predefined scoring rule rather than independent flood-prediction performance**" (P603). Present it as a validity correction made when the labeling dependency was understood.

**Q3. You proposed two sensor nodes and a monsoon season of data. You have one node and a short pilot.**
Single sensor node, prototype deployment, no full river-system coverage (P252); the pilot was limited in duration and local conditions (P242); the field test observed only low-water Receding conditions, which is precisely why the fuzzy layer was verified by sweeping its full input space (768 combinations, 3,150 grid points) instead of relying on field events (P528–P529).

**Q4. Only two respondents?**
Two BDRRMC focal persons, chosen purposively as the personnel directly involved in DRRM and barangay-level decisions (P431); the thesis states the result is preliminary and not generalizable to all officials or residents (P433, P569). The six dimensions (functionality, usability, reliability, perceived contribution, attitude toward use, intention to use) come from the TAM-based instrument in Appendix C.

**Q5. Why did the title drop "AI"?**
Have one prepared line. The defensible version: the system is a hybrid Random Forest + fuzzy-logic pipeline, which the thesis describes as AI throughout, and the title was narrowed to the offline-first framing. Note that the acronym's own expansion still contains "AI" (P107) — if that tension is not resolved in the file, expect the follow-up.

**Q6. Your accuracy is 94.26%. What does that prove?**
What the thesis says: the model reproduces rule-derived Low/Medium/High labels with high agreement on a held-out test set (345 of 366) — and because those labels come from the same features, this is consistency, not independent flood-prediction accuracy (P603). Add the useful detail: High recall was 0.9524 (60 of 63) while High precision was 0.8824 because eight Medium-labeled samples were classified High (P522), and the four documented flood events classified 2 High / 2 Medium (P533ff., P108).

**Q7. What happened to the Alert, Alarm and Critical levels — did the system ever produce them?**
Not in the field: the deployment recorded only Receding low-water conditions (P528). Those regimes were covered by the functional sweep — all four classes were reachable and the output was monotonic in water level and rate of rise (P529), and 296 of 768 combinations (38.5%) were resolved by an explicit rule with the remainder handled by the weighted fallback (P530).

**Q8. Your proposal had one author; the thesis has five.**
Answer truthfully about contributions (§1, item 2 of the material table). The authorship, approval sheet, and title page all changed consistently (P34–P38, P47) — what did **not** change is the bionotes section, which still covers only the original author (§8).

**Q9. 13,568 records in a short deployment — including 2.500 m readings and negative water levels?**
The thesis reports these as data-quality findings, not river behaviour (P590, Table 4.5): 67 zero-distance records with a corresponding 2.500 m reading, 124 negative calculated water levels, and five implausibly short raw distances — all flagged for quality review. Presenting them unprompted is a strength; the panel may ask what the 2.500 m median-adjacent outlier implies for the recorded range of −0.012 m to 2.500 m (P543).

**Q10. Total cost?**
**₱27,920** (Table 3.2, revised actual-parts BOM) against **₱28,200** in the proposal — edge station ₱19,050, river node ₱7,070, general materials ₱1,800; the paid Weather Forecast API line is gone entirely because Open-Meteo is free. The former multi-unit-row follow-up (§10, item 12) is resolved by the revision.

---

## 12. Addendum (post-review, 2026-10-22) — a model-family benchmark now exists

This addendum supersedes nothing above. It scopes one item whose status has changed since the delta was written, and states plainly what has *not* changed.

**What was added.** A model comparison that the proposal never promised and the thesis does not report: four model families trained and evaluated on the same stratified 80/20 split with `random_state=42` and the shipped hyperparameters.

| Model | Accuracy | Macro F1 | F1 (High) |
|---|---|---|---|
| Logistic Regression | 0.9126 | 0.8974 | 0.8750 |
| Decision Tree | 0.9180 | 0.9057 | 0.8923 |
| **Random Forest (shipped)** | **0.9426** | 0.9329 | 0.9160 |
| Gradient Boosting | 0.9536 | 0.9423 | 0.9173 |

A chronological 80/20 evaluation of the same Random Forest gives **0.8962** accuracy (macro F1 0.8906) against 0.9426 stratified — a 4.6-point drop that confirms the thesis's own caveat that a random split over rolling-window features may inflate apparent generalization performance.

**What this does and does not change.**

- **§9 row 1 and §11 Q1 remain accurate exactly as written.** The proposal's commitment (RQ3 P225; method P334; instrumentation P380; benefits P406) was to compare the model against **a traditional threshold-based warning method**. That comparison still was not completed and is still future work (P344) — it needs documented flood events to stand a baseline against, and four events cannot support it. The benchmark above is a **model-family comparison**: it asks which classifier best reproduces the rule, not whether the rule-based system outperforms an operational threshold method. **Do not let the benchmark be heard as the threshold baseline.**
- **§5's literature line (P122) is now incomplete.** "No substantially new literature was added for the Random Forest or fuzzy-logic choice" remains true of the *document*, but the Random Forest justification in Chapter 2 (P307 Refadah; Mesias & Bagtasa) is no longer the whole answer. The empirical supplement says something the literature cannot: four very different model families land within about four points of each other, because the target is a deterministic threshold function of the same eight inputs. That is the circularity of §10 made visible.
- **The framing moves from "uncompared" to "compared, and the comparison does not claim a win."** Random Forest was the defensible default, not the top scorer — gradient boosting scored 0.9536 against our 0.9426. Say it that way. `possible_question.md`, `FLAIRE Defense Script.md` (B3) and `FLAIRE Thesis Cheat Sheet.md` all use this framing.
- **The thesis document itself is unchanged by this addendum.** If the benchmark is to be reported in the thesis, that is a new Chapter 4 table and paragraph. If it is not, the benchmark stays a defense-side answer. **Decide before printing** — a number that exists in the repository but not in the thesis must not be presented as a thesis finding.

---

*Prepared from a full-text, table-inclusive extraction of both documents. Paragraph indices (`P###`) are stable identifiers from that extraction and can be used to jump straight to any cited passage for a final read-through.*
