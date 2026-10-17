# FLAIRE Thesis — Independent Review Report (Third Pass)

**Artifact:** FLAIRE Thesis 2 - 1 (Revised).docx — 828 paragraphs, 13 tables
**Scope:** Full re-read after stage-9 revisions; regression check against passes 1 and 2; defense-readiness assessment; team briefing.
**Read-only review — no files were modified.**

---

**Operational note:** the stage-9 insertion shifted all paragraph numbers after P606 by +1. References is now **P639** (was P638); the acceptability conclusion is now P610; recommendations are now P622–P633. Cross-references from earlier reports must be adjusted accordingly.

---

## 0. Post-Review Update — Flood-Event Dates Corrected

> **After this review was completed, the four documented flood-event dates were corrected against the barangay records** — to 21/10/2021, 30/03/2022, 27/12/2022, and 23/11/2023 (previously 07/10/2021, 26/03/2022, 23/12/2022, 19/11/2023). The E2 result therefore changed from **0 of 4 High** to **2 of 4 High** (the other two Medium). The affected text was revised in the abstract (P108), Table 4.4, and paragraphs P537, P538, P587, P605, P606, and P622; P606's wording was revised accordingly. Statements below that cite the old 0/4 figure are marked *(corrected — see this note)*.
>
> **The substantive conclusions are unaffected.** The model's verdict matched the rule-derived class on all four dates, so the core finding stands: the model reproduces the scoring rule rather than encoding flood occurrence, and the feature set represents rainfall rather than floods. The two events it flagged as High are the two with the strongest accumulated-rainfall signals — i.e. the two the rule already flags; the two misses carried only moderate rainfall.

---

## 1. Stage-9 Verification

### Appendix C (P716–P756): Landed, coherent, and better-designed than it looks

The instrument is complete: respondent note (P718), direction line (P719), scale legend (P720), six parts, 4 Likert items each, 24 items total (P723–P756). Verified against everything it touches:

- **Respondent note (P718)** — "administered to the BDRRMC focal persons of Brgy. Elvita" — matches P447, P251, RQ5 (P236), and Table 4.6 exactly. The phantom-respondent problem from the first review stays dead.
- **Scale direction (P720)** — 5 = Strongly Agree … 1 = Strongly Disagree — matches P447 in direction. Consistent.
- **Six dimensions** match P440–P446 and Table 4.6's rows one-for-one, including the "Perceived" qualifiers on reliability and preparedness.
- **The arithmetic check is the load-bearing detail.** With n = 2 respondents and 4 items per dimension, each dimension has 8 responses: 5.00 × 8 = 40 (all 5s), and 4.75 × 8 = **38 — an integer**, realizable as integer Likert responses. Had 5 items per dimension been used, 4.75 × 10 = 47.5 — **not an integer** — and Table 4.6's usability figure would have been arithmetically impossible. Four items per dimension is exactly what makes the reported table reconstructible — the kind of consistency that survives an examiner with a calculator.
- **Item wording** tracks the actual system: item 1 = LoRa water-level/rainfall (P366), item 2 = dashboard risk display (P376), item 3 = offline classification (P370), item 14 = MDRRMO complementarity (**MDRRMO used correctly**), items 21–24 = intention constructs mapping onto the TAM framing in P440–P446.

**The one weak item is item 4** (P726): *"The system notifies users of high-risk conditions through the dashboard and SMS alerts"* — rated 5.00 as part of the Functionality average. Two exposures: it is **double-barreled** (dashboard *and* SMS in one statement — a methods examiner's favorite target), and it asks about an SMS capability that was never demonstrated to these respondents and never fired in the field (no Alarm/Critical was ever reached; P633 says so). It survives as a *perceived*-functionality item in a TAM survey — respondents rate what they were shown and told — with P570's precedent (juxtaposing perceived reliability against actual deployment behavior) as intellectual cover. If the panel reads Appendix C closely, item 4 is where they will push. **Prepared answer:** "Perception of demonstrated capability, not a field-delivery claim; SMS triggers only on Alarm/Critical, which the deployment never produced."

**No contradictions found** with P440–P448, Table 4.6, or RQ5. The reconstruction caveat (author to check against the real administered form) is right — the one thing that must match reality is the **item count per dimension**, since the 4.75 in Table 4.6 is only reconstructible at 4 items × n = 2.

### AI-layer rationale (P224 + new P606): Landed, coherent, no contradictions — with one philosophical nit

- **P224** now ends: "…and to explore whether machine-learning models can be used to assist in assessing flood risk at the barangay scale." Grammatical; sits naturally after the demonstration aim; consistent with the Abstract's "technical feasibility" framing and with P606.
- **P606** is well-placed (after P605, before the deployment conclusions — it closes the model-results block P603–P605) and its three-move structure is exactly right: feasibility established (RF ran on edge hardware, high rule-agreement), predictive usefulness **not** established (same-eight-features labels, and a four-event check in which the model merely matched the rule), value pending independent labels + water-level/tide features + chronological validation. This answers the W3 gap. It does not conflict with P603, P604, or P605 — it *synthesizes* them at the level the aims clause poses. Mild restatement of the four-event and circular-labels facts — normal for a conclusions chapter, trimmable, not a defect.
- **The nit:** P606 answers a question that appears in neither the Statement of the Problem (P228–P236) nor any RQ — the aims paragraph (P224) poses it, the conclusions (P606) answer it, and the SOP never asks it. Defensible (aims outrank questions in most local thesis templates; RQ3's rule-reproduction question operationalizes the feasibility half), and adding a sixth RQ was a conscious choice. **Prepared answer to "Is this a question of the study or not?":** "It is an aim; RQ3 operationalizes the feasibility half; P606 states plainly that the usefulness half remains open."

---

## 2. Regression Check: Nothing regressed; nothing grew; Appendix C is the only delta

Re-verified every known-remaining item in the current file: References placeholder (**P639**), blank in-text citation years in the literature review (P282–P308 double-space holes — "The GSMA␣␣report," "Gray␣␣of the ITU," "Cacal, Austria, and Taboada␣␣conducted" — all still present), TOC blank (P153–P161), List of Tables entries 4.1–4.6 without page numbers (P166–P171), Gantt grid still empty against P460's narrative describing filled bars (Table 2), Acknowledgement empty (P74+), Appendices A/B/D–G still empty headers, bionotes Betita-only with duplicated cells (Tables 10–11) and a dangling "CURRICULUM VITAE" heading (P827), chronology still P44 "January 2026" vs P503 "October 11, 2026," MDRRMC/MDRRMO inconsistent (MDRRMC at P416–P418, P432, P472, P622; MDRRMO elsewhere including the abbreviation list and Appendix C item 14), P448 "pilot-tested" strain unchanged.

The stage-9 edits were surgical: clean sentences, no seams, no dangling cross-references, no double words. One new observation (not a regression): P448's "pilot-tested before formal administration" reads slightly more strained now that the instrument is visible in Appendix C — with a total population of two focal persons, a panelist will ask who the pilot was administered to. Minor; one clarifying clause if the actual pilot process is recallable.

---

## 3. Updated Verdict: MAJOR REVISIONS — completion-only, unchanged in kind, one item closer

Against the baseline: Appendix C — the only completion item that had substantive content risk — is now filled and verified sound, and W3 (the last open argument defect) is closed in-text at P224/P606. **The substantive ledger across all three reviews is now empty: no argument-level objection remains in this document.**

The verdict does not convert because the mandatory-container items remain: a thesis with no reference list (P639), no in-text citation years, five of seven appendices empty, no acknowledgement, an empty Gantt, four missing co-author bionotes/CVs, and a blank TOC cannot receive Minor Revisions — there is nothing "minor" about a missing bibliography.

Be clear about the size of what remains: **this is an assembly job, not a thinking job.** Bibliography insertion (plus filling the ~15 in-text year slots — do not forget those, or no citation will match any reference entry), appendix content already in hand, a drawn Gantt, five short bionotes, a generated TOC, and one date fix on the title page. The author-handled chronology is the only item on that list with defense-day consequences if skipped. When those land, expect clearance at **Accept with minor copyedits** (MDRRMO harmonization, P448 clause, List-of-Tables page numbers).

---

## 4. Re-Ranked Top 5 Defense Questions (current text)

1. **"The title page says January 2026; your deployment data says October 2026. Which is it?"** — Rises to #1 by sheer certainty: still unfixed (P44 vs P503). No in-text answer exists. **Must be fixed before the defense, not explained at it.**
2. **"Your labels came from the same eight features and a four-event check in which it merely matched its own rule *(corrected — see §0)*. What did the AI layer add?"** — Still the most-asked technical question, but **its damage has collapsed**: stand on P224 (stated aim: *explore whether* ML can assist) and P606 (answered: feasibility yes, predictive usefulness no, with the path to establish it). W3 is downgraded from "unanswerable in text" to "answerable in one sentence with a page reference." Prepare the follow-up — *"Why include the RF at all, then?"* — answer: exploratory inclusion inside an architecture designed to absorb independent labels later, plus it supplies the propensity input the fuzzy layer consumes (P371).
3. **"Only 2 of your 4 documented floods were classified High — and both were the ones your own rule already flags *(corrected — see §0)*. Why should the BDRRMC trust this system?"** — In-text answers exist at every step: P587 (event check and diagnosis), P605/P606 (cannot yet be shown to identify real floods), P632 (decision-support, human-confirmation required), P633 (higher classes must be re-deployed until exercised). No improvisation needed.
4. **"Appendix C item 4 got a 5.00 for SMS alerts — did anyone ever receive an SMS? P377 says it 'automatically sends.'"** — Slightly more likely now that the instrument is in the document. Answer: SMS is Alarm/Critical-triggered, the deployment never left Receding (P544, P633), so none fired; the item measures perceived capability. Have the deployed-unit config evidence ready (the repo copy shows `SMS_ENABLED = False`; the author attests the Pi runs True — a panelist who reads the repo will ask).
5. **"38.5% rule resolution — 61.5% of your fuzzy layer is a hand-tuned fallback. Who validated those weights?"** — Unchanged. P530 discloses the split; the fallback weights are hand-set design constants in the code; all four of Table 4.3's representative outputs correspond to explicit rules 1, 4, 6, 8 — the thesis doesn't state that, but the student can.

**Demoted off the list:** "Chapter 3 promised false-alarm rate and lead time" — dead since stage 8 (P345 fixed).
**Next tier:** the P224-aim-vs-SOP mismatch (§1 nit) and "pilot-tested on whom" (P448) with n = 2.

---

## 5. Team Briefing (for the four co-authors)

**What FLAIRE is.** FLAIRE is a flood early-warning prototype built for Barangay Elvita in Narra, Palawan — a riverbank community that floods seasonally and gets its warnings from municipality-wide advisories that don't say whether *this* barangay is affected. FLAIRE is "offline-first": a solar-powered sensor node measures the river's water level and rainfall and sends it by LoRa radio (no internet needed) to a Raspberry Pi 5 computer. The Pi stores everything locally, shows a dashboard over the local network, and runs two AI layers: a Random Forest model that sorts the weather picture into Low/Medium/High "flood propensity," and a 20-rule fuzzy-logic classifier that combines that propensity with the live water level, how fast it is rising, forecast rain, and tide to produce one of four risk levels: Receding, Alert, Alarm, Critical. When it reaches Alarm or Critical, it can send SMS to barangay officials. All of it cost about ₱23,700.

**What actually exists.** The software is real and runs (20 rules implemented exactly as the thesis table shows). A real field deployment happened beside the bridge in Elvita in October 2026 — but it only produced about 21.5 hours of data instead of the planned 47, because the battery died, and the water never rose above low level. Two BDRRMC focal persons tried the system and rated it highly. **What is still missing from the document:** the reference list (with citation years), most appendices, the Gantt chart, four co-authors' bionotes/CVs, the acknowledgement, the table of contents, and a date fix (the title page says January 2026 but the deployment happened in October 2026 — this must be corrected).

**What the evidence does and does not show.** The Random Forest scores 94.26% accuracy — but only against labels the team's own scoring rule generated from the same eight features, so it shows the model can imitate that rule, *not* that it predicts floods. A check against four real documented flood events classified 2 of 4 as High — and on all four the model agreed with the rule *(corrected — see §0)*; the thesis reports this plainly (P537, P587, P606). The field test proved the sensor-and-logging pipeline works outdoors; it never exercised Alert/Alarm/Critical and proved nothing about warning lead time. The acceptability ratings come from two people and are explicitly labeled preliminary.

**What each of you should be able to say if questioned.**
1. "The 94.26% is agreement with our own labeling rule, and the thesis says so in the abstract and conclusions — we're honest that flood-prediction skill is not yet established."
2. "The AI layer was included to explore whether machine learning can assist barangay-scale flood assessment; P606 answers that: technically feasible, predictive value still to be demonstrated."
3. "It's decision-support, not an autonomous alarm — the BDRRMC always makes the final call."

Never claim it forecast a flood, never claim lead time was measured, never claim SMS was field-tested.

**Three things that must happen before submission:**
1. Insert the real reference list **and fill every in-text citation year** — many in Chapter 2 are blank.
2. Fix the January 2026 vs October 2026 date contradiction on the title page.
3. Fill the remaining appendices, Gantt bars, acknowledgement, table of contents, and all five bionotes/CVs.

None of these require new thinking — only assembly. **The argument is done; the container isn't.**
