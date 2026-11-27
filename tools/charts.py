"""Regenerate the inline SVG charts in index.html from the paper's tables.

Inline (not <img>) so the SVG picks up the theme's CSS variables and reveal.js fragments.

    python3 tools/charts.py index.html
"""

import math
import re
import sys
from pathlib import Path

# Tables 3 and 4: AUC in the test week on the languages ORES supports, plus the one number section 5.2 gives for the
# languages it doesn't. Every orange column is the shipped model. On anonymous edits a model trained on them alone
# reaches 0.80, one more point, but it loses on all edits, so the paper doesn't ship it and the chart doesn't show it.
# Column labels are lists of lines: the columns are too narrow for the rule's name on one line.
RANKING_GROUPS = [
    ("all edits", [(["flag every", "anonymous edit"], 0.75, "rule"), (["ORES"], 0.84, "general"),
                   (["this paper"], 0.88, "specialised")]),
    ("anonymous edits only", [(["ORES"], 0.70, "general"), (["this paper"], 0.79, "specialised")]),
    ("languages without ORES", [(["ORES"], None, "general"), (["this paper"], 0.873, "specialised")]),
]

# Table 3 (AUC, all edits) next to Table 5 (DIR), each configuration with its text models. Without them AUC is
# 0.01–0.02 lower and DIR moves by under 0.2, so the slide states that in words instead of adding rows.
FAIRNESS_GROUPS = [
    ("BASELINE", [("ORES", 0.84, 20.02, "general")]),
    ("THIS PAPER · WITH TEXT MODELS", [("trained on anonymous edits", 0.79, 2.06, "specialised"),
                    ("trained on all edits", 0.84, 3.08, "specialised"),
                    ("+ who edited", 0.88, 9.54, "specialised")]),
]
DIR_BASE = 7.93

# Not from the paper, which never checks calibration: our retrained copy of the shipped configuration (all users +
# user + text-model features, wikipedia-mgr run pwmmeagu) scored on the authors' test week, 1,079,265 edits, all 47
# languages. Edits are grouped around 0, 0.1, …, 1 (±0.05); each point is (mean score, share reverted) of a group.
# The points sit on the curve that balanced class weights predict, odds scaled by (1 − π) / π with π = 0.08.
MEASURED_CALIBRATION = [
    (0.032, 0.003), (0.099, 0.009), (0.194, 0.020), (0.296, 0.031), (0.398, 0.046), (0.499, 0.069),
    (0.599, 0.102), (0.700, 0.149), (0.801, 0.229), (0.899, 0.403), (0.974, 0.722),
]

# Figure 7, one point per language (train · all): share of edits reverted, share made anonymously. Read off the
# figure by pixel position (±0.002); only the languages named on the slide are identified.
LANGUAGE_RATES = [
    (0.008, 0.042), (0.02, 0.041), (0.027, 0.043), (0.028, 0.099), (0.029, 0.057), (0.04, 0.105), (0.042, 0.07),
    (0.043, 0.106), (0.045, 0.114), (0.047, 0.463), (0.049, 0.205), (0.05, 0.091), (0.051, 0.098), (0.051, 0.144),
    (0.051, 0.267), (0.053, 0.078), (0.054, 0.083), (0.054, 0.115), (0.057, 0.145), (0.059, 0.105), (0.062, 0.126),
    (0.063, 0.108), (0.064, 0.242), (0.066, 0.093), (0.071, 0.195), (0.072, 0.148), (0.074, 0.209), (0.074, 0.393),
    (0.081, 0.167), (0.083, 0.15), (0.083, 0.154), (0.083, 0.189), (0.084, 0.172), (0.087, 0.2), (0.09, 0.097),
    (0.093, 0.204), (0.094, 0.214), (0.1, 0.325), (0.106, 0.283), (0.108, 0.195), (0.113, 0.129), (0.134, 0.34),
    (0.135, 0.224), (0.152, 0.111), (0.158, 0.291), (0.177, 0.155), (0.268, 0.347),
]
# Label anchor per named point: (text-anchor, dx, dy), placed clear of neighbouring dots.
LANGUAGE_NAMES = {
    (0.047, 0.463): ("Malay", "end", -14, 6),
    (0.074, 0.393): ("Korean", "start", 14, 6),
    (0.051, 0.267): ("Japanese", "start", 14, 6),
    (0.049, 0.205): ("Chinese", "middle", 0, 30),
    (0.087, 0.2): ("English", "middle", 0, -18),
    (0.083, 0.154): ("Polish", "end", -12, -14),
    (0.268, 0.347): ("Hindi", "end", -14, 6),
    (0.177, 0.155): ("Arabic", "start", 14, 6),
    (0.152, 0.111): ("Persian", "end", -14, 6),
}

# Figure 12, the best model's top 8 features by mean |SHAP| (log-odds), read off the bars by pixel position
# (±0.002). The kind follows the paper's feature groups: user features are is_anonymous and the user groups.
# Ranks 9–12 (visual editor, inserts a link, size change, changed-text model) are all below 0.11 and only add rows.
FEATURE_IMPORTANCE = [
    ("editor is anonymous", 0.323, "who"),
    ("which language edition", 0.308, "meta"),
    ("user group: editor", 0.247, "who"),
    ("user group: autopatrolled", 0.244, "who"),
    ("edit made on mobile", 0.231, "meta"),
    ("text model: page title", 0.179, "text"),
    ("user group: extended confirmed", 0.158, "who"),
    ("user group: administrator", 0.120, "who"),
]
FEATURE_KINDS = [("who", "who edited"), ("text", "text model"), ("meta", "edit metadata")]

# Our reproduction (thesis repo wikipedia-mgr) against the authors' values, as (paper, ours) pairs.
# - Paper: the unrounded numbers their notebooks print (src/wikirevert/repro/targets.py), which Tables 3–5 round.
#   Table 2 only exists in the paper, to 3 decimals.
# - Ours, final model, ORES subset, 6 configurations, both stages ours. The three with text models come from run
#   `mlm-full` (outputs/repro/mlm-full/report.md): our trees on our own retrained BERTs' scores. The three without
#   never read BERT scores, so they come from run `full`. Each is scored on the test file whose text features match
#   its training population, as the paper did. AUC and precision come in pairs per configuration: all users, then
#   anonymous ones.
# - Ours, text models: experiments/notes/2026-10-31-hubert-repro-mlm.md, the insert/remove/change models, each in its
#   own slice (all-tuned on all users, anon-tuned on anonymous users). The title model isn't in Table 2.
# Panel: title, pairs, axis range, ticks, tick format.
REPRO_PANELS = [
    ("AUC", [(0.7702, 0.7688), (0.7681, 0.7681), (0.7916, 0.7900), (0.8010, 0.8014), (0.8171, 0.8162),
             (0.7510, 0.7508), (0.8373, 0.8403), (0.7840, 0.7892), (0.8702, 0.8698), (0.7617, 0.7615),
             (0.8795, 0.8815), (0.7925, 0.7972)],
     (0.74, 0.90), [0.75, 0.80, 0.85, 0.90], "{:.2f}"),
    ("precision at 75% recall", [(0.1406, 0.1377), (0.3965, 0.3963), (0.1523, 0.1481), (0.4382, 0.4382),
                                 (0.1821, 0.1801), (0.3779, 0.3781), (0.2010, 0.2037), (0.4162, 0.4232),
                                 (0.2670, 0.2647), (0.3870, 0.3873), (0.2821, 0.2835), (0.4259, 0.4337)],
     (0.10, 0.46), [0.1, 0.2, 0.3, 0.4], "{:.1f}"),
    ("DIR", [(1.98, 1.97), (2.06, 2.02), (2.91, 2.90), (3.08, 3.12), (9.36, 9.37), (9.54, 9.59)],
     (0, 10.5), [0, 5, 10], "{:g}×"),
    ("stage 1 text models", [(0.745, 0.7742), (0.742, 0.7644), (0.662, 0.6654), (0.757, 0.7665), (0.752, 0.7591),
                           (0.681, 0.7028)],
     (0.64, 0.80), [0.65, 0.70, 0.75, 0.80], "{:.2f}"),
]


def ranking_chart() -> str:
    # The axis starts at 0.5, random order, not at 0: no model here is worse than random, and from 0 the gaps vanish.
    lo, hi = 0.5, 0.9
    x_start, col_w, col_gap, group_gap = 80, 130, 12, 56
    top, base = 56, 356

    def sy(v: float) -> float:
        return base - (v - lo) / (hi - lo) * (base - top)

    cols, groups = [], []
    x = x_start
    for name, entries in RANKING_GROUPS:
        first = x
        for label, v, family in entries:
            cols.append((x, label, v, family))
            x += col_w + col_gap
        groups.append((name, (first + x - col_gap) / 2))
        x += group_gap - col_gap
    width = x - group_gap + 20

    out = [
        f'<svg class="chart ranking" viewBox="0 0 {width} {base + 96}" role="img" '
        'aria-label="AUC of ORES and of the paper\'s model on all edits, on anonymous edits and on languages without '
        'ORES, from Tables 3 and 4">'
    ]
    out.append('<text class="axis-title" x="0" y="22">AUC · 0.5 = random order, 1 = every reverted edit first</text>')
    for tick in [0.5, 0.6, 0.7, 0.8, 0.9]:
        out.append(f'<line class="grid" x1="{x_start}" y1="{sy(tick):.1f}" x2="{width - 20}" y2="{sy(tick):.1f}" />')
        out.append(f'<text x="{x_start - 12}" y="{sy(tick) + 7:.1f}" text-anchor="end">{tick:.1f}</text>')
    out.append(f'<line class="axis" x1="{x_start}" y1="{base}" x2="{width - 20}" y2="{base}" />')

    for cx, label, v, family in cols:
        mid = cx + col_w / 2
        if v is None:
            out.append(f'<text class="no-model" x="{mid:.1f}" y="{base - 40}" text-anchor="middle">no ORES'
                       f'<tspan x="{mid:.1f}" dy="24">model</tspan></text>')
        else:
            out.append(f'<rect class="bar {family}" x="{cx}" y="{sy(v):.1f}" width="{col_w}" height="{base - sy(v):.1f}" />')
            cls = "bar-value best" if family == "specialised" else "bar-value"
            out.append(f'<text class="{cls}" x="{mid:.1f}" y="{sy(v) - 10:.1f}" text-anchor="middle">{v:.2f}</text>')
        lines = "".join(f'<tspan x="{mid:.1f}" dy="{0 if i == 0 else 22}">{line}</tspan>' for i, line in enumerate(label))
        out.append(f'<text class="col-label" x="{mid:.1f}" y="{base + 28}" text-anchor="middle">{lines}</text>')
    for name, gx in groups:
        out.append(f'<text class="panel-title" x="{gx:.1f}" y="{base + 86}" text-anchor="middle">{name}</text>')

    out.append("</svg>")
    return "\n".join(out)


def fairness_chart() -> str:
    # Bars start at zero, not at 1× ("equal"), so "triples" and "2.5× the data" read as ratios of bar lengths.
    label_w, bar_w, max_dir, auc_x = 300, 700, 21, 1120
    top, group_h, row_h, bar_h = 40, 40, 56, 38

    def sx(dir_: float) -> float:
        return label_w + dir_ / max_dir * bar_w

    rows, groups = [], []
    y = top
    for group, entries in FAIRNESS_GROUPS:
        groups.append((group, y + 26))
        y += group_h
        for entry in entries:
            rows.append((y, *entry))
            y += row_h
    axis_y = y + 4
    grid_top = top + group_h

    out = [
        f'<svg class="chart fairness" viewBox="0 0 {auc_x + 60} {axis_y + 62}" role="img" '
        'aria-label="How many times as often each model flags anonymous edits as registered ones, with its AUC, '
        'from Tables 3 and 5">'
    ]
    # No panel title: the DIR formula above the chart on the slide already says what a bar measures.
    for group, gy in groups:
        out.append(f'<text class="group" x="0" y="{gy}">{group}</text>')
    # Table 3's AUC is over all edits; without saying so it reads as AUC on the anonymous edits the bars are about.
    out.append(f'<text class="col-head" x="{auc_x}" y="{groups[0][1] - 26}" text-anchor="middle">AUC'
               f'<tspan x="{auc_x}" dy="26">all edits</tspan></text>')
    # No 0× label: at this scale it would touch 1×, and the axis line already starts at zero.
    for tick in [1, 5, 10, 15, 20]:
        x = sx(tick)
        out.append(f'<line class="grid" x1="{x:.1f}" y1="{grid_top}" x2="{x:.1f}" y2="{axis_y}" />')
        out.append(f'<text x="{x:.1f}" y="{axis_y + 28}" text-anchor="middle">{tick}×</text>')
    out.append(f'<text x="{sx(1):.1f}" y="{axis_y + 54}" text-anchor="middle">equal</text>')
    out.append(f'<line class="axis" x1="{label_w}" y1="{axis_y}" x2="{label_w + bar_w}" y2="{axis_y}" />')

    for ry, label, _, d, family in rows:
        out.append(f'<text class="bar-label" x="{label_w - 14}" y="{ry + bar_h - 8}" text-anchor="end">{label}</text>')
        out.append(f'<rect class="bar {family}" x="{label_w}" y="{ry + 3}" width="{sx(d) - label_w:.1f}" height="{bar_h}" />')

    # Drawn over the bars so it stays visible across ORES's, and before the values so their halo masks it.
    xb = sx(DIR_BASE)
    out.append(f'<line class="ref-line" x1="{xb:.1f}" y1="{top - 4}" x2="{xb:.1f}" y2="{axis_y}" />')
    out.append(f'<text class="ref-label" x="{xb:.1f}" y="{top - 14}" text-anchor="middle">'
               f"really reverted {DIR_BASE}× as often</text>")

    best = max(r[2] for r in rows)
    for ry, _, auc, d, _ in rows:
        out.append(f'<text class="bar-value" x="{sx(d) + 8:.1f}" y="{ry + bar_h - 8}">{d:.1f}×</text>')
        cls = "auc-value best" if auc == best else "auc-value"
        out.append(f'<text class="{cls}" x="{auc_x}" y="{ry + bar_h - 8}" text-anchor="middle">{auc:.2f}</text>')

    out.append("</svg>")
    return "\n".join(out)


def targets_chart() -> str:
    # Same scale as the fairness bars, so the two slides read as one picture.
    x0, x1, max_dir = 40, 1140, 21
    axis_y = 150
    ores = FAIRNESS_GROUPS[0][1][0]
    paper = FAIRNESS_GROUPS[1][1][-1]
    targets = [(1, "1× · flag both groups equally"), (DIR_BASE, f"{DIR_BASE}× · mirror the reverts (the paper's aim)")]

    def sx(dir_: float) -> float:
        return x0 + dir_ / max_dir * (x1 - x0)

    out = [
        f'<svg class="chart targets" viewBox="0 0 1180 {axis_y + 44}" role="img" '
        'aria-label="The two candidate targets for the flagging gap, and where ORES and the paper\'s model land, '
        'from Table 5">'
    ]
    for tick in [1, 5, 10, 15, 20]:
        out.append(f'<text x="{sx(tick):.1f}" y="{axis_y + 30}" text-anchor="middle">{tick}×</text>')
        out.append(f'<line class="grid" x1="{sx(tick):.1f}" y1="{axis_y - 8}" x2="{sx(tick):.1f}" y2="{axis_y}" />')
    out.append(f'<line class="axis" x1="{x0}" y1="{axis_y}" x2="{x1}" y2="{axis_y}" />')
    for value, label in targets:
        out.append(f'<line class="ref-line" x1="{sx(value):.1f}" y1="52" x2="{sx(value):.1f}" y2="{axis_y}" />')
        out.append(f'<text class="ref-label" x="{sx(value) - 4:.1f}" y="38">{label}</text>')
    for (name, _, dir_, family), anchor, dx in [(paper, "start", 22), (ores, "end", -22)]:
        x = sx(dir_)
        out.append(f'<circle class="pt {family}" cx="{x:.1f}" cy="112" r="13" />')
        out.append(f'<text class="pt-label" x="{x + dx:.1f}" y="120" text-anchor="{anchor}">'
                   f'{"this paper" if family == "specialised" else name} · {dir_:.1f}×</text>')
    out.append("</svg>")
    return "\n".join(out)


def prior_chart() -> str:
    x0, x1, y0, y1 = 64, 590, 392, 44

    def sx(score: float) -> float:
        return x0 + score * (x1 - x0)

    def sy(share: float) -> float:
        return y0 - share * (y0 - y1)

    out = [
        f'<svg class="chart prior" viewBox="0 0 {x1 + 20} {y0 + 58}" role="img" '
        'aria-label="Score against the share of edits really reverted, measured on the test week for our copy of '
        'the paper\'s model">'
    ]
    out.append('<text class="axis-title" x="0" y="20">share of edits with that score that get reverted</text>')
    for tick in [0, 0.2, 0.4, 0.6, 0.8, 1]:
        out.append(f'<line class="grid" x1="{x0}" y1="{sy(tick):.1f}" x2="{x1}" y2="{sy(tick):.1f}" />')
        out.append(f'<text x="{x0 - 10}" y="{sy(tick) + 5:.1f}" text-anchor="end">{tick:.0%}</text>')
        out.append(f'<line class="grid" x1="{sx(tick):.1f}" y1="{y1}" x2="{sx(tick):.1f}" y2="{y0}" />')
        out.append(f'<text x="{sx(tick):.1f}" y="{y0 + 24}" text-anchor="middle">{tick:g}</text>')
    out.append(f'<line class="axis" x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" />')
    out.append(f'<text class="axis-title" x="{(x0 + x1) / 2}" y="{y0 + 52}" text-anchor="middle">'
               "score the model outputs</text>")

    angle = math.degrees(math.atan2(sy(1) - sy(0), sx(1) - sx(0)))
    out.append(f'<line class="ref-line" x1="{sx(0)}" y1="{sy(0)}" x2="{sx(1)}" y2="{sy(1)}" />')
    lx, ly = sx(0.4), sy(0.4) - 12
    out.append(f'<text class="ref-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
               f'transform="rotate({angle:.1f} {lx:.1f} {ly:.1f})">calibrated: score = share reverted</text>')

    points = " ".join(f"{sx(s):.1f},{sy(r):.1f}" for s, r in MEASURED_CALIBRATION)
    out.append(f'<polyline class="curve-prior" points="{points}" />')
    for s, r in MEASURED_CALIBRATION:
        out.append(f'<circle class="pt" cx="{sx(s):.1f}" cy="{sy(r):.1f}" r="6" />')
    # Sits in the gap between the diagonal and the curve's steep end, the only open area next to the curve.
    out.append(f'<text class="series-small" x="{sx(0.84):.1f}" y="{sy(0.54):.1f}" text-anchor="end">the paper\'s'
               f'<tspan x="{sx(0.84):.1f}" dy="24">model, measured</tspan></text>')

    score, reverted = min(MEASURED_CALIBRATION, key=lambda point: abs(point[0] - 0.5))
    px, py = sx(score), sy(reverted)
    out.append(f'<line class="guide" x1="{px:.1f}" y1="{py - 10:.1f}" x2="{px:.1f}" y2="{sy(0.14):.1f}" />')
    # "Of edits scored 0.5", not "at score 0.5": the latter reads as a threshold, i.e. all edits scored 0.5 or more.
    # Worded like the slide's definition bullet ("of edits scored 0.3, 30% get reverted"); no room for an "only"
    # before the curve, and the diagonal blocks moving the label left.
    out.append(f'<text class="callout" x="{sx(0.33):.1f}" y="{sy(0.24):.1f}">of edits scored 0.5,'
               f'<tspan x="{sx(0.33):.1f}" dy="24">{reverted:.0%} get reverted</tspan></text>')
    out.append(f'<circle class="pt" cx="{px:.1f}" cy="{py:.1f}" r="8" />')
    out.append("</svg>")
    return "\n".join(out)


def least_squares(xs: list[float], ys: list[float]) -> tuple[float, float]:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - slope * mx, slope


def languages_chart() -> str:
    # Anonymous share across, revert share up: the fitted line predicts a wiki's reverts from its anonymous editing.
    # Figure 7 has the axes the other way round.
    x0, x1, y0, y1 = 64, 680, 380, 40
    x_hi, y_hi = 0.50, 0.28

    def sx(rate: float) -> float:
        return x0 + rate / x_hi * (x1 - x0)

    def sy(rate: float) -> float:
        return y0 - rate / y_hi * (y0 - y1)

    out = [
        f'<svg class="chart langs" viewBox="0 0 {x1 + 20} {y0 + 58}" role="img" '
        'aria-label="Share of edits reverted against share made anonymously, one point per language, from Figure 7, '
        'with a straight-line fit">'
    ]
    out.append('<text class="axis-title" x="0" y="20">edits reverted</text>')
    for tick in [0, 0.05, 0.1, 0.15, 0.2, 0.25]:
        out.append(f'<line class="grid" x1="{x0}" y1="{sy(tick):.1f}" x2="{x1}" y2="{sy(tick):.1f}" />')
        out.append(f'<text x="{x0 - 10}" y="{sy(tick) + 5:.1f}" text-anchor="end">{tick:.0%}</text>')
    for tick in [0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        out.append(f'<line class="grid" x1="{sx(tick):.1f}" y1="{y1}" x2="{sx(tick):.1f}" y2="{y0}" />')
        out.append(f'<text x="{sx(tick):.1f}" y="{y0 + 24}" text-anchor="middle">{tick:.0%}</text>')
    out.append(f'<line class="axis" x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" />')
    out.append(f'<text class="axis-title" x="{(x0 + x1) / 2}" y="{y0 + 52}" text-anchor="middle">'
               "edits made without logging in</text>")

    reverted = [r for r, _ in LANGUAGE_RATES]
    anonymous = [a for _, a in LANGUAGE_RATES]
    intercept, slope = least_squares(anonymous, reverted)
    out.append(f'<line class="ref-line" x1="{sx(0):.1f}" y1="{sy(intercept):.1f}" '
               f'x2="{sx(x_hi):.1f}" y2="{sy(intercept + slope * x_hi):.1f}" />')
    for point in LANGUAGE_RATES:
        cls = "pt lang named" if point in LANGUAGE_NAMES else "pt lang"
        out.append(f'<circle class="{cls}" cx="{sx(point[1]):.1f}" cy="{sy(point[0]):.1f}" r="6" />')
    for (rx, ry), (name, anchor, dx, dy) in LANGUAGE_NAMES.items():
        out.append(f'<text class="pt-label" x="{sx(ry) + dx:.1f}" y="{sy(rx) + dy:.1f}" text-anchor="{anchor}">{name}</text>')
    out.append("</svg>")
    return "\n".join(out)


def features_chart() -> str:
    label_w, x0, x1 = 340, 356, 1150
    hi = 0.35
    top, row_h, bar_h = 56, 40, 28
    axis_y = top + len(FEATURE_IMPORTANCE) * row_h + 4

    def sx(v: float) -> float:
        return x0 + v / hi * (x1 - x0)

    out = [
        f'<svg class="chart features" viewBox="0 0 {x1 + 20} {axis_y + 60}" role="img" '
        'aria-label="Top features by mean absolute SHAP value, from Figure 12">'
    ]
    kx = x0
    for kind, name in FEATURE_KINDS:
        out.append(f'<rect class="bar kind-{kind}" x="{kx}" y="8" width="20" height="20" />')
        out.append(f'<text class="key-label" x="{kx + 30}" y="26">{name}</text>')
        kx += 60 + len(name) * 12
    for tick in [0, 0.1, 0.2, 0.3]:
        out.append(f'<line class="grid" x1="{sx(tick):.1f}" y1="{top}" x2="{sx(tick):.1f}" y2="{axis_y}" />')
        out.append(f'<text x="{sx(tick):.1f}" y="{axis_y + 26}" text-anchor="middle">{tick:g}</text>')
    out.append(f'<line class="axis" x1="{x0}" y1="{axis_y}" x2="{x1}" y2="{axis_y}" />')
    # Mean |SHAP| is in log-odds, not in the 0–1 score: a push of 0.3 moves the score by different amounts at
    # different starting points.
    out.append(f'<text class="axis-title" x="{x1}" y="{axis_y + 54}" text-anchor="end">'
               "how far the feature moves an edit's log-odds of revert, on average</text>")
    for i, (name, value, kind) in enumerate(FEATURE_IMPORTANCE):
        y = top + i * row_h
        out.append(f'<text class="bar-label" x="{label_w}" y="{y + bar_h - 2}" text-anchor="end">{name}</text>')
        out.append(f'<rect class="bar kind-{kind}" x="{x0}" y="{y + 4}" width="{sx(value) - x0:.1f}" height="{bar_h}" />')
    out.append("</svg>")
    return "\n".join(out)


def reproduction_chart() -> str:
    size, step, x_start, top = 220, 290, 60, 46
    bottom = top + size
    out = [
        f'<svg class="chart repro" viewBox="0 0 1170 {bottom + 62}" role="img" '
        'aria-label="Our reproduced numbers against the paper\'s, one panel per metric">'
    ]
    out.append(f'<text class="axis-title" x="16" y="{top + size / 2:.1f}" text-anchor="middle" '
               f'transform="rotate(-90 16 {top + size / 2:.1f})">ours</text>')

    for i, (title, pairs, (lo, hi), ticks, tick_fmt) in enumerate(REPRO_PANELS):
        x0 = x_start + i * step

        def sx(v: float, x0: float = x0, lo: float = lo, hi: float = hi) -> float:
            return x0 + (v - lo) / (hi - lo) * size

        def sy(v: float, lo: float = lo, hi: float = hi) -> float:
            return bottom - (v - lo) / (hi - lo) * size

        out.append(f'<text class="panel-title" x="{x0 + size / 2:.1f}" y="{top - 18}" text-anchor="middle">{title}</text>')
        for tick in ticks:
            out.append(f'<line class="grid" x1="{sx(tick):.1f}" y1="{top}" x2="{sx(tick):.1f}" y2="{bottom}" />')
            out.append(f'<line class="grid" x1="{x0}" y1="{sy(tick):.1f}" x2="{x0 + size}" y2="{sy(tick):.1f}" />')
            out.append(f'<text x="{sx(tick):.1f}" y="{bottom + 24}" text-anchor="middle">{tick_fmt.format(tick)}</text>')
            out.append(f'<text x="{x0 - 8}" y="{sy(tick) + 6:.1f}" text-anchor="end">{tick_fmt.format(tick)}</text>')
        out.append(f'<line class="axis" x1="{x0}" y1="{bottom}" x2="{x0 + size}" y2="{bottom}" />')
        out.append(f'<line class="ref-line" x1="{x0}" y1="{bottom}" x2="{x0 + size}" y2="{top}" />')
        out.append(f'<text class="axis-title" x="{x0 + size / 2:.1f}" y="{bottom + 50}" text-anchor="middle">paper</text>')

        for paper, ours in pairs:
            out.append(f'<circle class="pt" cx="{sx(paper):.1f}" cy="{sy(ours):.1f}" r="6" />')

    out.append("</svg>")
    return "\n".join(out)


CHARTS = {
    "ranking": ranking_chart,
    "fairness": fairness_chart,
    "targets": targets_chart,
    "prior": prior_chart,
    "langs": languages_chart,
    "features": features_chart,
    "repro": reproduction_chart,
}


def main(path: str) -> None:
    html = Path(path).read_text()
    for name, render in CHARTS.items():
        pattern = re.compile(rf"(<!-- chart:{name} -->).*?(<!-- /chart:{name} -->)", re.S)
        if not pattern.search(html):
            sys.exit(f"marker chart:{name} not found in {path}")
        html = pattern.sub(lambda m: f"{m.group(1)}\n{render()}\n{m.group(2)}", html)
    Path(path).write_text(html)


if __name__ == "__main__":
    main(sys.argv[1])
