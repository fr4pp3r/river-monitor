# -*- coding: utf-8 -*-
"""
Generate the FLAIRE thesis-defense deck as a PowerPoint file.

Source of truth: presentation/index.html (self-contained 16-slide HTML deck).
This script mirrors its content, layout and dark-teal visual theme.

Output: presentation/FLAIRE Presentation.pptx (16:9, 12192000 x 6858000 EMU)

Rerunnable:  py -3 generate_pptx.py
"""

import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE as MSO_LINE

HERE = Path(__file__).resolve().parent
OUT = HERE / "FLAIRE Presentation.pptx"

# ---------------------------------------------------------------- theme ----
# Mirrors the CSS :root variables in index.html
BG      = RGBColor.from_string("0c2228")   # --bg
SURFACE = RGBColor.from_string("14323a")   # --surface
BORDER  = RGBColor.from_string("32636e")   # --border
INK     = RGBColor.from_string("e8f2f5")   # --ink
MUTED   = RGBColor.from_string("9fc0c8")   # --muted
DIM     = RGBColor.from_string("6e939c")   # --dim
TEAL    = RGBColor.from_string("3ec7b3")   # --teal
AMBER   = RGBColor.from_string("f4b942")   # --amber
ORANGE  = RGBColor.from_string("e67e3b")   # --orange
RED     = RGBColor.from_string("c95252")   # --red
PALE    = RGBColor.from_string("8fd0c8")   # link/highlight teal
DARKNUM = RGBColor.from_string("072226")   # text on teal chips/numbers

# solid approximations of the HTML's translucent fills (alpha over --bg)
FIG_BG   = RGBColor.from_string("102930")  # figbox rgba(20,50,58,.45)
BLANK_BG = RGBColor.from_string("0e262c")  # blank-zone rgba(20,50,58,.22)
CALL_OK  = RGBColor.from_string("103538")  # callout.ok  rgba(62,199,179,.09)
CALL_OFF = RGBColor.from_string("21302b")  # callout.off rgba(244,185,66,.09)
CALL_WARN= RGBColor.from_string("1f272c")  # callout.warn rgba(201,82,82,.10)
CHIP_R   = RGBColor.from_string("133839")  # chip.r  rgba(62,199,179,.13)
CHIP_A   = RGBColor.from_string("2a362b")  # chip.c(alpha amber mix) unused
BAR_BG   = RGBColor.from_string("1e3138")  # .bar rgba(255,255,255,.07)

SANS  = "Segoe UI"
SERIF = "Georgia"

M  = 0.6          # page margin (inches)  ~ HTML 60px
SW = 13.333       # slide width
SH = 7.5          # slide height
CW = SW - 2 * M   # content width = 12.133

prs = Presentation()
prs.slide_width = Emu(12192000)   # 13.333 in
prs.slide_height = Emu(6858000)   # 7.5 in
BLANK = prs.slide_layouts[6]      # blank layout


# --------------------------------------------------------------- helpers ---
def new_slide(notes=""):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def textbox(slide, x, y, w, h, anchor=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if anchor is not None:
        tf.vertical_anchor = anchor
    return tf


def _run(p, text, color, bold, italic, size, font):
    r = p.add_run()
    r.text = text
    f = r.font
    f.name = font
    f.size = Pt(size)
    f.color.rgb = color
    f.bold = bold
    f.italic = italic
    return r


def para(tf, segs, size=12, align=None, space_after=None, space_before=None,
         line_spacing=None, first=False):
    """segs: list of (text, color[, bold[, italic[, font]]]) tuples."""
    p = tf.paragraphs[0] if (first and not tf.paragraphs[0].runs) else tf.add_paragraph()
    if align is not None:
        p.alignment = align
    if space_after is not None:
        p.space_after = Pt(space_after)
    if space_before is not None:
        p.space_before = Pt(space_before)
    if line_spacing is not None:
        p.line_spacing = line_spacing
    for seg in segs:
        text = seg[0]
        color = seg[1] if len(seg) > 1 and seg[1] is not None else INK
        bold = bool(seg[2]) if len(seg) > 2 else False
        italic = bool(seg[3]) if len(seg) > 3 else False
        font = seg[4] if len(seg) > 4 and seg[4] else SANS
        _run(p, text, color, bold, italic, size, font)
    return p


def spaced(run, hundredths):
    """Letter-spacing, in 1/100 pt (mirrors CSS letter-spacing)."""
    run._r.get_or_add_rPr().set("spc", str(hundredths))


def rect(slide, x, y, w, h, fill=None, line=None, line_w=1.0, dash=False,
         rounded=False, radius=0.08):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded:
        try:
            sh.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(line_w)
        if dash:
            sh.line.dash_style = MSO_LINE.DASH
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return sh


def header(slide, kicker, title, deck=None, title_size=23):
    tf = textbox(slide, M, 0.34, CW, 0.3)
    p = para(tf, [(kicker, TEAL, True)], size=10, first=True)
    spaced(p.runs[0], 260)
    tf = textbox(slide, M, 0.58, CW, 0.6)
    para(tf, [(title, INK, True, False, SERIF)], size=title_size, first=True)
    if deck:
        tf = textbox(slide, M, 1.14, CW, 0.28)
        p = para(tf, [(deck, MUTED, True)], size=9.5, first=True)
        spaced(p.runs[0], 60)
        return 1.5
    return 1.34


def bullets(slide, items, x, y, w, size=12, gap=7, color=INK):
    """Teal round bullet + text, mirroring ul.bullets."""
    tf = textbox(slide, x, y, w, SH - y - M)
    first = True
    for item in items:
        p = para(tf, [("\u25cf  ", TEAL), (item, color)], size=size,
                 space_after=gap, first=first)
        if first:
            p.runs[0].font.size = Pt(max(size - 4, 7))
        first = False
    return tf


def stat_card(slide, x, y, w, h, num, lab, accent=TEAL, num_size=20, lab_size=8):
    rect(slide, x, y, w, h, fill=SURFACE, line=BORDER, line_w=1.0, rounded=True, radius=0.1)
    bar = rect(slide, x + 0.08, y + 0.03, w - 0.16, 0.045, fill=accent)
    bar.line.fill.background()
    tf = textbox(slide, x + 0.14, y + 0.16, w - 0.28, h - 0.28, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, [(num, INK, True, False, SERIF)], size=num_size, align=PP_ALIGN.CENTER, first=True)
    p = para(tf, [(lab, MUTED, True)], size=lab_size, align=PP_ALIGN.CENTER,
             space_before=3)
    spaced(p.runs[0], 120)


def figbox(slide, x, y, w, h, desc, caption=None, label="◲ FIGURE PLACEHOLDER · DROP IMAGE TO INSERT"):
    """Replaceable figure placeholder: dashed border + teal label + muted desc.
    Presenter swaps it for a real picture later."""
    rect(slide, x, y, w, h, fill=FIG_BG, line=BORDER, line_w=1.5, dash=True,
         rounded=True, radius=0.06)
    tf = textbox(slide, x + 0.25, y, w - 0.5, h, anchor=MSO_ANCHOR.MIDDLE)
    p = para(tf, [(label, TEAL, True)], size=8.5, align=PP_ALIGN.CENTER, first=True)
    spaced(p.runs[0], 200)
    if desc:
        para(tf, [(desc, MUTED)], size=9.5, align=PP_ALIGN.CENTER, space_before=6)
    if caption:
        cap_x = max(0.0, x - 1.0)
        cap_w = min(SW - cap_x, w + 2.0) if x - 1.0 >= 0 else w + 2 * x
        tfc = textbox(slide, cap_x, y + h + 0.06, cap_w, 0.3)
        p = para(tfc, [(caption, DIM, True)], size=8.5, align=PP_ALIGN.CENTER, first=True)
        spaced(p.runs[0], 100)


def chip(slide, x, y, w, text, border_col, text_col, fill_col, h=0.42, size=10):
    sh = rect(slide, x, y, w, h, fill=fill_col, line=border_col, line_w=1.2,
              rounded=True, radius=0.3)
    tf = sh.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = para(tf, [(text, text_col, True)], size=size, align=PP_ALIGN.CENTER, first=True)
    spaced(p.runs[0], 100)


def callout(slide, x, y, w, h, border_col, fill_col, segs, size=10):
    rect(slide, x, y, w, h, fill=fill_col, line=border_col, line_w=1.2,
         rounded=True, radius=0.08)
    tf = textbox(slide, x + 0.22, y + 0.1, w - 0.44, h - 0.2, anchor=MSO_ANCHOR.MIDDLE)
    first = True
    for segline in segs:
        para(tf, segline, size=size, space_after=3, first=first)
        first = False


def card_head(tf, title, color, size=10, width_chars=None):
    p = para(tf, [(title, color, True)], size=size, first=True)
    spaced(p.runs[0], 110)
    return p


# ================================================================ slides ===

# ---------------------------------------------------------------- 1 · Title
notes = ("Open with the problem: advisories are municipality-wide — they don't say "
         "whether this barangay is affected — and connectivity drops when warnings "
         "matter most.")
s = new_slide(notes)
tf = textbox(s, 0, 1.28, SW, 0.32)
p = para(tf, [("Thesis Oral Defense", TEAL, True)], size=11, align=PP_ALIGN.CENTER, first=True)
spaced(p.runs[0], 280)

tf = textbox(s, 0, 1.68, SW, 1.15)
para(tf, [("FLAIRE", INK, True, False, SERIF)], size=63, align=PP_ALIGN.CENTER, first=True)

tf = textbox(s, 0, 2.95, SW, 0.45)
para(tf, [("Flood Level AI Risk Evaluation", MUTED)], size=19, align=PP_ALIGN.CENTER, first=True)

tf = textbox(s, 0, 3.5, SW, 0.6)
para(tf, [("An offline-first flood early-warning prototype · Barangay Elvita, Narra, Palawan",
           PALE, True)], size=12.5, align=PP_ALIGN.CENTER, first=True)

tf = textbox(s, 0, 4.02, SW, 0.35)
para(tf, [("[Candidate Name] · [Adviser] · [Date]", MUTED)], size=11.5,
     align=PP_ALIGN.CENTER, first=True)

chips = [("Solar LoRa node", 2.0, TEAL, RGBColor.from_string("a7eedf"), CHIP_R),
         ("Raspberry Pi 5", 1.8, TEAL, RGBColor.from_string("a7eedf"), CHIP_R),
         ("RF + fuzzy logic", 1.95, TEAL, RGBColor.from_string("a7eedf"), CHIP_R),
         ("≈ ₱27,920", 1.5, RED, RGBColor.from_string("e8a3a3"), RGBColor.from_string("2a2a2e"))]
tot_w = sum(c[1] for c in chips) + 0.15 * (len(chips) - 1)
cx = (SW - tot_w) / 2
for text, w, bcol, tcol, fillc in chips:
    chip(s, cx, 4.6, w, text, bcol, tcol, fillc)
    cx += w + 0.15

tf = textbox(s, 0, 5.55, SW, 0.35)
para(tf, [("Decision-support tool — the BDRRMC makes the call.", DIM)], size=10.5,
     align=PP_ALIGN.CENTER, first=True)


# --------------------------------------------- 2 · Background of the study
s = new_slide("Placeholder slide per user request — insert background-of-study "
              "material here before the defense.")
header(s, "02 · Background of the study", "Background of the study")
rect(s, M, 1.62, CW, 5.25, fill=BLANK_BG, line=DIM, line_w=1.75, dash=True,
     rounded=True, radius=0.05)
tf = textbox(s, 2.0, 3.4, SW - 4.0, 1.6, anchor=MSO_ANCHOR.MIDDLE)
p = para(tf, [("CONTENT / FIGURE PLACEHOLDER", RGBColor.from_string("9fc0c8"), True)],
         size=11, align=PP_ALIGN.CENTER, first=True)
spaced(p.runs[0], 180)
para(tf, [("Add background-of-study material here — flood context of Barangay Elvita, "
           "Narra, Palawan, existing warning practices, and related literature. "
           "Intended to be replaced.", MUTED)],
     size=11.5, align=PP_ALIGN.CENTER, space_before=10)


# --------------------------------------------- 3 · Statement of the problem
s = new_slide("Statement of the problem from thesis Chapter 1: current flood-warning "
              "limitations in Brgy. Elvita and the five research questions FLAIRE "
              "seeks to answer.")
header(s, "03 · STATEMENT OF THE PROBLEM", "Statement of the problem")

# teal left-border quote
qtext = ("Flooding is a persistent threat in Brgy. Elvita, Narra, Palawan — a flood-vulnerable "
         "barangay along a major river system with limited structural flood-mitigation works, "
         "unreliable internet connectivity, and continued reliance on manual observation and "
         "threshold-based warnings. Existing centralized systems can be unreachable during "
         "network outages, and few documented implementations combine offline, edge-based "
         "hybrid AI analytics for rural barangay deployment. FLAIRE addresses this gap.")
qb = rect(s, M, 1.2, 0.045, 1.06, fill=TEAL)
tf = textbox(s, M + 0.2, 1.24, CW - 0.3, 1.0)
para(tf, [(qtext, MUTED, False, True)], size=10, first=True, line_spacing=1.15)

questions = [
    "What are the key problems and limitations in current flood-warning practices and data "
    "utilization in Brgy. Elvita, Narra, Palawan, and how can these be addressed through an "
    "offline-first, AI-based flood early-warning system?",

    "How can a Fuzzy-AI riverine flood-risk classification system be designed and developed "
    "for Brgy. Elvita that integrates cached seven-day weather and tide forecast data from "
    "OpenMeteo (updated at least daily, every six hours, and stored in a local database); "
    "real-time water-level and rainfall data from a LoRa-based hydrological sensor node "
    "transmitted to a Raspberry Pi 5 edge device; a hybrid AI pipeline in which a Random "
    "Forest model estimates flood propensity using R1, R3, R7, rain_days, TMAX, TMIN, "
    "TideMax, and TideMin while a fuzzy-logic classifier with 20 rules classifies flood risk "
    "as Receding, Alert, Alarm, or Critical; and a local web dashboard accessible through a "
    "LAN, enabling BDRRMC personnel to monitor real-time sensor data, AI-based risk "
    "classifications, and visualizations without internet connectivity, with alerts "
    "delivered through the dashboard and SMS?",

    "How consistently does the Random Forest flood-propensity model reproduce the "
    "rule-derived Low, Medium, and High flood-propensity categories on a held-out test set, "
    "in terms of accuracy, precision, recall, and F1-score?",

    "How did the FLAIRE prototype perform during a limited field deployment in terms of "
    "sensor-data capture, data logging, and data quality?",

    "How acceptable is the developed FLAIRE system to the BDRRMC focal persons of Brgy. "
    "Elvita, Narra, Palawan in terms of functionality, usability, reliability, perceived "
    "contribution to disaster preparedness, attitude toward use, and intention to use, as "
    "measured through a Technology Acceptance Model (TAM)-based interview or survey?",
]
heights = [0.6, 1.22, 0.62, 0.42, 0.64]
yy = 2.44
for n, (q, hh) in enumerate(zip(questions, heights), start=1):
    ov = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(M), Inches(yy), Inches(0.34), Inches(0.34))
    ov.fill.solid(); ov.fill.fore_color.rgb = TEAL
    ov.line.fill.background(); ov.shadow.inherit = False
    otf = ov.text_frame; otf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(otf, [(str(n), DARKNUM, True, False, SERIF)], size=12, align=PP_ALIGN.CENTER, first=True)
    tf = textbox(s, M + 0.5, yy - 0.02, CW - 0.5, hh + 0.15)
    para(tf, [(q, INK)], size=10.5, first=True, line_spacing=1.08)
    yy += hh + 0.1


# ---------------------------------------------- 4 · Significance of study
s = new_slide("Beneficiaries per thesis Chapter 1: BDRRMC, barangay officials and "
              "residents, the academic community, and policy-makers / future deployments.")
header(s, "04 · Significance of the study", "Significance of the study",
       "Who benefits")
benefits = [
    ("BDRRMC (Barangay Elvita)",
     "Offline-first, AI-enhanced flood early-warning: flood-risk classifications from "
     "real-time sensor data and cached forecasts through a LAN dashboard — supporting "
     "informed decisions, preemptive evacuation planning, and resource allocation even "
     "during internet or power interruptions."),
    ("Barangay officials & residents",
     "Timely flood notifications through SMS alerts and dashboard-based monitoring, "
     "improving community preparedness and resilience in a flood-prone, low-connectivity "
     "setting."),
    ("Academic community",
     "A documented, reproducible offline-first hybrid Random Forest + fuzzy-logic "
     "flood-risk classification for a rural Philippine barangay, with an honest account of "
     "its labeling and validation limits."),
    ("Policy-makers & future deployments",
     "Evidence that barangay-scale early warning can run with minimal internet dependency "
     "and edge-based AI — an initial basis for scaling low-cost, power-resilient monitoring "
     "to similar communities."),
]
pos = [(M, 1.56), (M + 6.18, 1.56), (M, 3.28), (M + 6.18, 3.28)]
for (bx, by), (h3, body) in zip(pos, benefits):
    rect(s, bx, by, 5.95, 1.6, fill=SURFACE, line=BORDER, line_w=1.0,
         rounded=True, radius=0.07)
    tf = textbox(s, bx + 0.22, by + 0.13, 5.55, 1.35)
    card_head(tf, h3, TEAL, size=9.5)
    para(tf, [(body, INK)], size=9.5, space_before=4, line_spacing=1.1)
figbox(s, 4.67, 5.13, 4.0, 1.5,
       "Significance of the study — beneficiary map (BDRRMC, residents, researchers, policy).",
       caption="Figure 1. Significance of the study — beneficiaries.")


# ------------------------------------------- 5 · Scope and Delimitation
s = new_slide("Faithful to thesis Chapter 1: barangay-scale offline-first prototype, "
              "decision-support framing, n=2 acceptability survey, ~21.5 h deployment.")
header(s, "05 · Scope and Delimitation", "Scope and Delimitation",
       "In scope vs. boundaries")

scope_items = [
    "Design, development, and pilot deployment of FLAIRE — offline-first hybrid Fuzzy-AI "
    "riverine flood-risk classification and early-warning system, Brgy. Elvita, Narra, "
    "Palawan (one vulnerable river section)",
    "Historical data (PAGASA, NAMRIA) + cached Open-Meteo forecasts (6 h refresh), stored "
    "locally in SQLite",
    "LoRa sensor node → Raspberry Pi 5 edge device; RF flood propensity (8 features) + "
    "20-rule fuzzy logic → four risk levels",
    "LAN dashboard + SMS alerts; BDRRMC retains alert authority",
    "Held-out test-set evaluation (80/20) and TAM acceptability survey (n = 2 focal persons)",
]
delim_items = [
    "Riverine flooding only in Brgy. Elvita — excludes coastal flooding, upstream flash "
    "floods, areas outside the barangay",
    "Single sensor node; no full river-system coverage",
    "Decision support, not prediction: rule-derived labels; no measured forecast lead time; "
    "no threshold-baseline comparison",
    "Preliminary four-event check only; limited deployment duration (~21.5 h)",
    "n = 2 survey — preliminary, not generalizable",
    "Dependent on historical / forecast / real-time data availability and quality",
]

# In scope card
rect(s, M, 1.56, 5.95, 5.35, fill=SURFACE, line=BORDER, line_w=1.0, rounded=True, radius=0.05)
rect(s, M, 1.72, 0.045, 5.0, fill=TEAL)
tf = textbox(s, M + 0.28, 1.74, 5.45, 0.3)
card_head(tf, "In scope", TEAL, size=10)
bullets(s, scope_items, M + 0.45, 2.24, 5.3, size=11, gap=8)

# Delimitations card
dx = M + 6.18
rect(s, dx, 1.56, 5.95, 5.35, fill=SURFACE, line=BORDER, line_w=1.0, rounded=True, radius=0.05)
rect(s, dx, 1.72, 0.045, 5.0, fill=AMBER)
tf = textbox(s, dx + 0.28, 1.74, 5.45, 0.3)
card_head(tf, "Delimitations", AMBER, size=10)
bullets(s, delim_items, dx + 0.45, 2.24, 5.3, size=11, gap=8)


# ------------------------------------------ 6 · Entity relationship diagram
s = new_slide("ERD placeholder — insert the database diagram from DATABASE_ERD.md here.")
header(s, "06 · Entity relationship diagram", "Entity relationship diagram",
       "River-monitor database schema — insert figure")
figbox(s, 3.07, 1.8, 7.2, 4.0,
       "Entity-relationship diagram of the FLAIRE river-monitor database — insert the "
       "actual ERD image here.",
       caption="Figure 2. Entity-relationship diagram of the river-monitor database.")
tf = textbox(s, M, 6.35, CW, 0.3)
para(tf, [("Source material: DATABASE_ERD.md", DIM)], size=9, align=PP_ALIGN.CENTER, first=True)


# ------------------------------------- 7-9 · System flowcharts (figures 3-5)
def flow_slide(notes, kicker, title, deck, intro, desc, caption, source):
    s = new_slide(notes)
    header(s, kicker, title, deck)
    tf = textbox(s, M, 1.42, CW, 0.35)
    para(tf, [(intro, MUTED)], size=11.5, first=True)
    figbox(s, 3.17, 1.95, 7.0, 3.9, desc, caption=caption)
    tf = textbox(s, M, 6.4, CW, 0.3)
    para(tf, [(source, DIM)], size=9, align=PP_ALIGN.CENTER, first=True)
    return s

flow_slide(
    "Field sensor node segment: ultrasonic water-level + tipping-bucket rain gauge, "
    "on-board controller, LoRa RFM95W @ 915 MHz, 1-min cadence, solar/battery power.",
    "07 · SYSTEM FLOWCHART — NODE", "System flowchart — sensor node",
    "Field sensing segment",
    "The sensor node measures river water level and rainfall, then transmits readings "
    "over LoRa every minute.",
    "Sensor-node flowchart — sensors, controller, LoRa RFM95W @ 915 MHz, solar/battery power.",
    "Figure 3. Sensor-node flowchart.",
    "Source material: SYSTEM_FLOWCHART.md · thesis hardware (node side)")

flow_slide(
    "Raspberry Pi 5 edge segment: LoRa receiver, Open-Meteo cache, SQLite, RF+fuzzy AI "
    "pipeline, SMS handler (A7608e-H, Alarm/Critical only).",
    "08 · SYSTEM FLOWCHART — EDGE DEVICE", "System flowchart — edge device",
    "Raspberry Pi 5 segment",
    "The Raspberry Pi 5 edge node receives LoRa data, enriches it with cached forecasts, "
    "classifies risk, and handles alerts — all offline.",
    "Edge-device flowchart — LoRa receiver, forecast cache, SQLite, AI pipeline, SMS handler.",
    "Figure 4. Edge-device flowchart.",
    "Source material: SYSTEM_FLOWCHART.md · thesis edge layer")

flow_slide(
    "FastAPI web dashboard segment: LAN server, browser dashboard, BDRRMC review/confirm, "
    "SMS fan-out to contacts.",
    "09 · SYSTEM FLOWCHART — DASHBOARD", "System flowchart — dashboard",
    "FastAPI web dashboard segment",
    "The FastAPI dashboard serves BDRRMC personnel over LAN, showing live data and "
    "classifications, with human confirmation before public alerts.",
    "Dashboard flowchart — FastAPI server, browser dashboard, BDRRMC review, SMS fan-out.",
    "Figure 5. Dashboard flowchart.",
    "Source material: SYSTEM_FLOWCHART.md · thesis UI layer")


# -------------------------------------------------- 10 · Cost and benefits
s = new_slide("₱27,920 BOM — Node ₱7,070 · Edge ₱19,050 · General ₱1,800 — plus thesis "
              "benefit categories: technical, operational, community-level.")
header(s, "10 · COST AND BENEFITS", "Cost and benefits — about ₱27,920",
       "Bill of materials & expected benefits")

bom = {
    "Node": ("₱7,070", "25%", [
        ("Adafruit RFM95 LoRa", "₱2,500"),
        ("Mini magnets", "₱100"),
        ("Meshtastic 915 MHz LoRa antenna", "₱300"),
        ("Reed switch", "₱200"),
        ("MCP73871 power boost", "₱300"),
        ("UART 7.5 m waterproof ultrasonic sensor", "₱1,500"),
        ("3.5 W solar panel", "₱200"),
        ("3.7 V 10 Ah battery", "₱220"),
        ("Enclosure box", "₱250"),
        ("PVC pipe", "₱1,000"),
        ("Housing materials", "₱500"),
    ]),
    "Edge": ("₱19,050", "68%", [
        ("Meshtastic 915 MHz LoRa antenna", "₱300"),
        ("52Pi RPi5 power expansion board", "₱1,600"),
        ("Micro SD card", "₱750"),
        ("RPi5 active cooler", "₱250"),
        ("Raspberry Pi 5 2 GB board", "₱6,500"),
        ("12 V 12 Ah LiFePO4 battery pack", "₱2,220"),
        ("LoRa RFM95W transceiver board", "₱2,000"),
        ("60 W solar panel w/ controller", "₱1,900"),
        ("SIMCOM A7608e-H", "₱1,530"),
        ("SMS load (yearly)", "₱2,000"),
    ]),
    "General": ("₱1,800", "6%", [
        ("Breadboard (2 × 100)", "₱200"),
        ("Wires", "₱200"),
        ("Marine plywood", "₱400"),
        ("Miscellaneous electrical components", "₱1,000"),
    ]),
}

card_x = [("Node", M, 3.95), ("Edge", M + 4.08, 3.95), ("General", M + 8.16, 3.37)]
ROW_START = 1.46
CARD_H = 2.5
CARD_BOTTOM = ROW_START + CARD_H          # 3.96"
ROW_SIZE = 8
ROW_SPACE_AFTER = 0.5
# Rendered pitch per BOM row = single line height (1.2 em) + paragraph space-after,
# derived from font metrics rather than guessed. (Observed: size 8 + 1.5pt
# space-after actually renders ~0.154"/row, which caused the subtotal overlap.)
ROW_PITCH = (ROW_SIZE * 1.2 + ROW_SPACE_AFTER) / 72.0
ROW_TOP = ROW_START + 0.44

for name, bx, bw in card_x:
    sub_amt, pct, rows = bom[name]
    rect(s, bx, ROW_START, bw, CARD_H, fill=SURFACE, line=BORDER, line_w=1.0,
         rounded=True, radius=0.05)
    tf = textbox(s, bx + 0.18, ROW_START + 0.1, bw - 1.25, 0.28)
    p = para(tf, [(name, TEAL, True)], size=9, first=True)
    spaced(p.runs[0], 120)
    tf = textbox(s, bx + bw - 1.05, ROW_START + 0.06, 0.9, 0.3)
    para(tf, [(sub_amt, INK, True)], size=11, align=PP_ALIGN.RIGHT, first=True)
    # BOM rows — labels left, amounts right
    tf_l = textbox(s, bx + 0.18, ROW_TOP, bw - 1.1, CARD_H - 0.6)
    tf_r = textbox(s, bx + bw - 0.92, ROW_TOP, 0.75, CARD_H - 0.6)
    first = True
    for label, amt in rows:
        para(tf_l, [(label, INK)], size=ROW_SIZE, space_after=ROW_SPACE_AFTER, first=first)
        para(tf_r, [(amt, TEAL, True)], size=ROW_SIZE, align=PP_ALIGN.RIGHT,
             space_after=ROW_SPACE_AFTER, first=first)
        first = False
    last_row_bottom = ROW_TOP + len(rows) * ROW_PITCH
    sub_y = last_row_bottom + 0.05          # clear gap below the last item row
    bar_y = sub_y + 0.25                    # subtotal box is 0.25" tall
    # No overlap, by construction: last item bottom < subtotal top, and
    # subtotal + bar bottom <= card bottom (sub_y + 0.25 + 0.09 <= CARD_BOTTOM).
    assert last_row_bottom <= sub_y, (name, last_row_bottom, sub_y)
    assert bar_y + 0.09 <= CARD_BOTTOM, (name, bar_y + 0.09, CARD_BOTTOM)
    tf = textbox(s, bx + 0.18, sub_y, bw - 0.36, 0.25)
    para(tf, [("Subtotal — %s" % sub_amt, INK, True)], size=9, first=True)
    # cost bar
    rect(s, bx + 0.18, bar_y, bw - 0.36, 0.09, fill=BAR_BG, rounded=True, radius=0.5)
    fill_w = max((bw - 0.36) * int(pct.rstrip("%")) / 100.0, 0.09)
    rect(s, bx + 0.18, bar_y, fill_w, 0.09, fill=TEAL, rounded=True, radius=0.5)

# Total cost stat (big / amber accent, as in HTML .stat.big)
stat_card(s, M + 8.16, 4.1, 3.37, 1.0, "₱27,920", "Total build cost",
          accent=AMBER, num_size=19, lab_size=8)

# Benefits callout (amber border)
benefit_lines = [
    [("Benefits (thesis):", AMBER, True)],
    [("Technical — continuous water-level and rainfall monitoring without constant "
      "internet; local storage; RF + fuzzy-logic pipeline on the Pi 5; LAN dashboard.", INK)],
    [("Operational — continuous hydrological information and AI risk classifications for "
      "BDRRMC personnel; Receding classification under stable conditions; Alert / Alarm / "
      "Critical with SMS during heavy rainfall.", INK)],
    [("Community — improved situational awareness and earlier preparedness; reduced "
      "dependence on visual observation and municipality-wide MDRRMO alerts. Final alert "
      "authority stays with the BDRRMC — decision-support, not autonomous warning.", INK)],
]
callout(s, M, 4.1, 7.75, 1.62, AMBER, CALL_OFF, benefit_lines, size=8.5)

figbox(s, M + 8.16, 5.24, 3.37, 1.42,
       "Cost and benefits figure — benefit categories (technical, operational, "
       "community-level).",
       caption="Figure 6. Cost and benefits — benefit categories.")


# ------------------------------------------------- 11 · Results Q1 (Fig 7)
s = new_slide("Q1 findings (thesis Ch.4): manual rain gauge, visual observation, tide "
              "calendar; municipality-wide MDRRMO alerts; no continuous localized records.")
header(s, "11 · RESULTS AND DISCUSSION — Q1",
       "Results and discussion — Q1: Current practices & the warning gap",
       "Research question 1 — current flood-warning practices", title_size=20)
tf = textbox(s, M, 1.5, CW, 0.55)
para(tf, [("Q1: What are the key problems and limitations in current flood-warning "
           "practices and data utilization in Brgy. Elvita, and how can an offline-first, "
           "AI-based flood early-warning system address them?", MUTED)],
     size=10.5, first=True)
q1_bullets = [
    "Current monitoring relies on a manual rain gauge, visual river observation, and a "
    "tide calendar",
    "MDRRMO advisories cover the whole municipality — an alert may not mean Brgy. Elvita "
    "is affected",
    "Officials face uncertainty deciding whether an advisory needs local preparedness or "
    "response",
    "Network or power interruptions can limit communication and warning/response efforts",
    "No continuous, automated, barangay-specific water-level and rainfall records exist",
]
bullets(s, q1_bullets, M, 2.35, 6.55, size=11, gap=9)
figbox(s, 7.5, 2.5, 5.23, 2.94,
       "Current-practice / needs-assessment figure — manual monitoring, MDRRMO alerts, "
       "warning gap.",
       caption="Figure 7. Current-practice / needs-assessment figure.")


# ------------------------------------------------- 12 · Results Q2 (Fig 8)
s = new_slide("Q2 findings (thesis Ch.4): offline-first node→Pi→dashboard chain built; "
              "cached forecasts, RF+fuzzy pipeline, LAN dashboard + SMS all implemented.")
header(s, "12 · RESULTS AND DISCUSSION — Q2",
       "Results and discussion — Q2: System design & development",
       "Research question 2 — design requirements met", title_size=20)
tf = textbox(s, M, 1.5, CW, 0.55)
para(tf, [("Q2: How can a Fuzzy-AI riverine flood-risk classification system be designed "
           "and developed for Brgy. Elvita integrating cached forecasts, a LoRa sensor "
           "node, an RF+fuzzy pipeline, and a LAN dashboard?", MUTED)],
     size=10.5, first=True)
q2_bullets = [
    "✓ Offline-first: cached Open-Meteo weather/tide forecasts stored locally on the Pi 5",
    "✓ LoRa sensor node sends water-level + rainfall to the Raspberry Pi 5 edge device",
    "✓ Hybrid AI pipeline: RF flood propensity (8 features) → 20-rule fuzzy → 4 risk levels",
    "✓ Local SQLite database stores readings, forecasts, model outputs, and alerts",
    "✓ LAN dashboard shows live status, graphs, RF/fuzzy results, alert history — no "
    "internet needed",
    "✓ SMS via GSM modem (Alarm/Critical only); BDRRMC retains alert authority",
]
bullets(s, q2_bullets, M, 2.35, 6.7, size=11, gap=9)
figbox(s, 7.5, 2.9, 5.23, 2.94,
       "System output / requirements-verification figure — offline-first chain end to end.",
       caption="Figure 8. System output / requirements-verification figure.")


# ------------------------------------------------- 13 · Results Q3 (Fig 9)
s = new_slide("Q3 findings (thesis Ch.4): RF 94.26% accuracy, macro F1 0.933 on held-out "
              "set; labels rule-derived so consistency ≠ prediction skill; 2 of 4 "
              "documented flood events matched the rule's High class.")
header(s, "13 · RESULTS AND DISCUSSION — Q3",
       "Results and discussion — Q3: Random Forest consistency",
       "Research question 3 — model vs. scoring rule", title_size=20)
tf = textbox(s, M, 1.5, CW, 0.35)
para(tf, [("Q3: How consistently does the Random Forest reproduce the rule-derived Low, "
           "Medium, and High flood-propensity categories on a held-out test set?", MUTED)],
     size=10.5, first=True)
stats_q3 = [("94.26%", "Accuracy", 17), ("0.933", "Macro F1", 17), ("0.943", "Weighted F1", 17),
            ("1,826", "Training records", 14), ("2 of 4", "Events matched rule", 14)]
sx = M
for num, lab, nsz in stats_q3:
    stat_card(s, sx, 1.95, 2.3, 0.78, num, lab, accent=TEAL, num_size=nsz,
              lab_size=7)
    sx += 2.3 + 0.155
q3_bullets = [
    "Trained 2020–2024 on PAGASA meteorological + NAMRIA tidal data (1,826 daily records)",
    "Random stratified 80/20 split (1,460 train / 366 test); no cross-validation",
    "Rule-derived labels (composite score ≥6.0 High, ≥3.0 Medium, <3.0 Low) from the same "
    "8 features",
    "Low F1 0.9728 · Medium F1 0.9099 · High F1 0.9160 · High recall 0.9524",
    "External probe: 2 of 4 documented flood events (2020–2025) classified High by the "
    "rule — diagnostic case check, not validation",
]
bullets(s, q3_bullets, M, 2.95, 6.8, size=10.5, gap=6)
warn_lines = [
    [("Honest caveat:", RED, True),
     (" 94.26% measures consistency with the study's own rule-derived labels — built from "
      "the same eight features — not demonstrated flood-prediction skill. Independent "
      "labels and chronological validation are needed.", INK)],
]
callout(s, M, 5.35, 6.85, 1.0, RED, CALL_WARN, warn_lines, size=9.5)
figbox(s, 7.75, 2.98, 5.0, 2.81,
       "Confusion matrix / feature-importance figure (hold-out test set, Random Forest).",
       caption="Figure 9. Confusion matrix / feature-importance figure.")


# ------------------------------------------------ 14 · Results Q4 (Fig 10)
s = new_slide("Q4 findings (thesis Ch.4): 13,568 records over ~21.5 h; battery died "
              "early; water stayed Receding/Low; sensor-logging pipeline validated.")
header(s, "14 · RESULTS AND DISCUSSION — Q4",
       "Results and discussion — Q4: Field deployment performance",
       "Research question 4 — limited field deployment", title_size=20)
tf = textbox(s, M, 1.5, CW, 0.55)
para(tf, [("Q4: How did the FLAIRE prototype perform during a limited field deployment in "
           "terms of sensor-data capture, data logging, and data quality?", MUTED)],
     size=10.5, first=True)
stats_q4 = [("21.5 h", "Logged", 15), ("13,568", "Records", 15)]
sx = M
for num, lab, nsz in stats_q4:
    stat_card(s, sx, 2.0, 2.3, 0.78, num, lab, accent=TEAL, num_size=nsz, lab_size=7)
    sx += 2.3 + 0.155
q4_bullets = [
    "Logged 13,568 LoRa records over ~21.5 h (intended ~47 h; battery depletion ended it "
    "early)",
    "Water level stayed in the Low band (≈0.01–0.18 m), below the 0.80 m alert threshold",
    "67 zero-distance, 124 negative, and 5 implausible-distance readings flagged for review",
    "River stayed Receding — Alert, Alarm, and Critical classes could not be exercised",
]
bullets(s, q4_bullets, M, 3.05, 6.7, size=11, gap=9)
figbox(s, 7.6, 2.95, 5.13, 2.89,
       "Deployment / water-level time-series figure — field records and battery curve.",
       caption="Figure 10. Deployment / water-level time-series figure.")


# ------------------------------------------------ 15 · Results Q5 (Fig 11)
s = new_slide("Q5 findings (thesis Ch.4): n=2 focal persons; five dimensions 5.00, "
              "usability 4.75; preliminary, not generalizable.")
header(s, "15 · RESULTS AND DISCUSSION — Q5",
       "Results and discussion — Q5: Acceptability (TAM)",
       "Research question 5 — user acceptability", title_size=20)
tf = textbox(s, M, 1.5, CW, 0.35)
para(tf, [("Q5: How acceptable is FLAIRE to the BDRRMC focal persons in terms of "
           "functionality, usability, reliability, preparedness, attitude, and intention "
           "to use?", MUTED)], size=10.5, first=True)
stats_q5 = [("n = 2", "Focal persons", 15), ("5.00", "Five dimensions", 15),
            ("4.75", "Usability", 15)]
sx = M
for num, lab, nsz in stats_q5:
    stat_card(s, sx, 2.0, 2.6, 0.78, num, lab, accent=TEAL, num_size=nsz, lab_size=7)
    sx += 2.6 + 0.18
q5_bullets = [
    "Two BDRRMC focal persons rated six TAM dimensions on a 5-point Likert scale",
    "Five dimensions (functionality, reliability, preparedness, attitude, intention): 5.00",
    "Usability: 4.75 — favorable initial feedback",
    "Small-n caveat: encouraging but not generalizable to all barangay officials/residents",
    "Perceived reliability read alongside deployment findings (battery depletion, "
    "anomalous readings)",
]
bullets(s, q5_bullets, M, 3.05, 6.7, size=11, gap=9)
figbox(s, 7.6, 2.95, 5.13, 2.89,
       "TAM survey results figure — acceptability ratings by dimension.",
       caption="Figure 11. TAM survey results figure.")


# --------------------------- 16 · Summary, Conclusion and Recommendation
s = new_slide("Three key findings, feasibility conclusion (decision-support, not "
              "prediction), four recommendations — then 'Thank you — questions?'.")
header(s, "16 · SUMMARY, CONCLUSION & RECOMMENDATION",
       "Summary, conclusion & recommendation",
       "Chapter 5 — what the study establishes", title_size=22)

final_cards = [
    (TEAL, "Summary — key findings", [
        "MDRRMO alerts are municipality-wide; monitoring gaps remain — current practice is "
        "manual (rain gauge, visual observation, tide calendar).",
        "RF reproduced its rule-derived labels (94.26% accuracy) — consistency, not "
        "independent flood-prediction skill.",
        "Pilot logged 13,568 records over ~21.5 h at Receding; battery depletion ended "
        "deployment; acceptability 5.00 / 4.75 (n = 2).",
    ]),
    (AMBER, "Conclusion", [
        "Feasibility established — the offline-first hybrid RF + fuzzy-logic prototype "
        "runs end-to-end on a Pi 5.",
        "Decision-support, not prediction — the BDRRMC makes the alert call.",
        "Human-in-the-loop alerting (SMS at Alarm / Critical, BDRRMC confirmation) is "
        "essential.",
    ]),
    (RED, "Recommendation", [
        "Use independent, BDRRMC-validated flood labels.",
        "Validate chronologically (e.g., train 2020–2023, test 2024).",
        "Harden power: panel placement, battery capacity, voltage monitoring.",
        "Expand the acceptability sample beyond n = 2.",
    ]),
]
for i, (accent, h3, items) in enumerate(final_cards):
    bx = M + i * (3.93 + 0.17)
    rect(s, bx, 1.56, 3.93, 4.0, fill=SURFACE, line=BORDER, line_w=1.0,
         rounded=True, radius=0.05)
    rect(s, bx, 1.75, 0.045, 3.65, fill=accent)
    tf = textbox(s, bx + 0.25, 1.72, 3.45, 0.3)
    card_head(tf, h3, accent, size=10)
    bullets(s, items, bx + 0.42, 2.18, 3.3, size=9.5, gap=8)

tf = textbox(s, 0, 5.95, SW, 0.4)
p = para(tf, [("Thank you — questions?", MUTED, True)], size=13,
         align=PP_ALIGN.CENTER, first=True)
spaced(p.runs[0], 160)


# ------------------------------------------------------------- save/verify --
prs.save(OUT)
print("Saved:", OUT)


def verify(path=OUT):
    """Reopen the file and assert 16 slides + readable titles."""
    check = Presentation(str(path))
    slides = list(check.slides)
    assert len(slides) == 16, "expected 16 slides, got %d" % len(slides)
    print("Slide count OK: 16")
    titles = []
    for i, sl in enumerate(slides, 1):
        best = None  # largest Georgia run on the slide = the title
        for sh in sl.shapes:
            if not sh.has_text_frame:
                continue
            for pgh in sh.text_frame.paragraphs:
                for r in pgh.runs:
                    if r.font.name == "Georgia" and r.font.size is not None:
                        if best is None or r.font.size > best[0]:
                            best = (r.font.size, r.text)
        t = best[1] if best else "(no title found)"
        titles.append(t)
        print("%2d. %s" % (i, t))
    return titles


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        verify()
    except Exception as exc:  # surface verification failures clearly
        print("VERIFICATION FAILED:", exc)
        sys.exit(1)
