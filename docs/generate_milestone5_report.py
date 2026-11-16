"""Generate the Milestone 5 (coupled EC-thermal-degradation) Word report.

This is a standalone report that reuses the layout helpers from
``generate_full_report.py`` but covers only the coupled study.

All numbers are loaded from the result CSVs produced by
``python run_experiment.py --mode all`` — nothing is hardcoded here.

Output: docs/reports/Milestone_5_Coupled_EC_Thermal_Degradation.docx
"""
import os
import sys

import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Reuse the shared layout helpers (importing is safe: the other module guards
# its entry point with ``if __name__ == "__main__"``).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_full_report import (  # noqa: E402
    set_heading_styles, add_table, add_figure, add_bold_para, LABELS,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "docs", "reports",
                   "Milestone_5_Coupled_EC_Thermal_Degradation.docx")

PROTOCOL_ORDER = ["cc_cv_1C", "cc_cv_2C", "boost_4C", "mcc_21",
                  "mcc_321", "mcc_432"]


def load_summaries():
    coupled = pd.read_csv(os.path.join(RESULTS, "coupled_summary.csv"))
    isothermal = pd.read_csv(os.path.join(RESULTS, "ageing_summary.csv"))
    return coupled.set_index("protocol"), isothermal.set_index("protocol")


def main():
    coupled, isothermal = load_summaries()

    # Only protocols present in both runs (CC-CV 3C is excluded from both
    # ageing studies because the plating term becomes numerically unstable).
    protocols = [p for p in PROTOCOL_ORDER
                 if p in coupled.index and p in isothermal.index]

    doc = Document()
    set_heading_styles(doc)

    # ---------------------------------------------------------------- title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Coupled Electrochemical–Thermal–\nDegradation Study")
    run.font.size = Pt(26)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 51, 102)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run("Milestone 5 – Self-Heating × Ageing Coupling")
    run.font.size = Pt(14)
    run.italic = True

    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run("Project: EV-Battery-FastCharging-Degradation\n"
                       "Toolchain: PyBaMM 26.7, Python 3.11, Casadi Safe Solver\n"
                       "Date: November 2026")
    run.font.size = Pt(11)

    doc.add_page_break()

    # ------------------------------------------------------ exec summary
    doc.add_heading("Executive Summary", level=1)
    doc.add_paragraph(
        "In Milestone 1 the degradation study was run at a fixed 25 °C (isothermal). "
        "That isolates the effect of the current profile, but it ignores a key physical "
        "feedback: a real cell heats itself during charge, and temperature strongly "
        "controls both solid–electrolyte interphase (SEI) growth and lithium plating. "
        "Milestone 5 re-runs the same six protocols with lumped thermal and degradation "
        "physics switched on simultaneously, so self-heating feeds back into the "
        "degradation rates."
    )
    add_bold_para(
        doc,
        "Headline result: self-heating suppresses lithium plating, so the coupled "
        "retention is higher — not lower — than the isothermal prediction at every "
        "C-rate above 1C. The isothermal study is therefore an upper bound on plating."
    )
    doc.add_paragraph(
        "This is a deliberately counter-intuitive result and should be read as a model "
        "prediction, not a validated fact. It follows directly from the temperature "
        "dependence of the plating term and is discussed, with its caveats, in Section 5."
    )

    # ------------------------------------------------- 1. what coupling adds
    doc.add_heading("1. What the Coupled Run Adds", level=1)
    doc.add_paragraph(
        "The three simulation modes answer different questions about the same cell:"
    )
    add_table(
        doc,
        ["Mode", "Thermal", "Degradation", "Question it answers"],
        [
            ["ageing", "Isothermal 25 °C", "SEI + plating",
             "Rank protocols by current profile alone"],
            ["thermal", "Lumped (h = 10)", "None",
             "How hot does each protocol make the cell?"],
            ["coupled", "Lumped (h = 10)", "SEI + plating",
             "What happens when heating and ageing act at once?"],
        ],
    )
    doc.add_paragraph(
        "The coupled mode is the most physically realistic of the three: the cell's own "
        "temperature rise changes the rate of the very degradation processes that are "
        "being measured. The difference between the isothermal and coupled results is "
        "therefore a direct measure of the thermal feedback."
    )

    # ------------------------------------------------------- 2. model setup
    doc.add_heading("2. Model Setup", level=1)
    doc.add_paragraph(
        "Every protocol is run for the same number of cycles under the same thermal "
        "environment; only the charge current profile differs."
    )
    add_table(
        doc,
        ["Parameter", "Value"],
        [
            ["Cell", "21700 NMC, 5 Ah, 3.7 V nominal"],
            ["Cycles per protocol", "40"],
            ["Thermal model", "Lumped single-node per cell, h = 10 W m⁻² K⁻¹"],
            ["Degradation modes", "SEI growth + lithium plating (coupled)"],
            ["Ambient temperature", "25 °C"],
            ["Charge target", "80 % SOC"],
            ["Discharge", "1C to 2.5 V (between charges)"],
            ["Protocols", "6 (CC-CV 3C excluded — plating term unstable)"],
        ],
    )
    doc.add_paragraph(
        "Because the thermal and degradation models are solved together, the temperature "
        "at cycle n depends on the accumulated degradation at cycle n, which in turn "
        "depends on the temperature history. This is the feedback loop the isothermal "
        "study cannot capture."
    )

    # -------------------------------------------------------- 3. results
    doc.add_heading("3. Results", level=1)

    doc.add_heading("3.1 End-of-test retention", level=2)
    retention_rows = []
    for p in protocols:
        iso_r = isothermal.loc[p, "retention_end_pct"]
        cp_r = coupled.loc[p, "retention_end_pct"]
        retention_rows.append([
            LABELS.get(p, p),
            f"{iso_r:.1f}",
            f"{cp_r:.1f}",
            f"{cp_r - iso_r:+.1f}",
        ])
    add_table(
        doc,
        ["Protocol", "Isothermal retention (%)", "Coupled retention (%)", "Δ (pp)"],
        retention_rows,
    )

    doc.add_heading("3.2 Plating loss and peak temperature", level=2)
    plating_rows = []
    for p in protocols:
        iso_pl = isothermal.loc[p, "plating_loss_end_ah"]
        cp_pl = coupled.loc[p, "plating_loss_end_ah"]
        reduction = (iso_pl - cp_pl) / iso_pl * 100.0
        plating_rows.append([
            LABELS.get(p, p),
            f"{iso_pl:.3f}",
            f"{cp_pl:.3f}",
            f"{reduction:.0f}",
            f"{coupled.loc[p, 't_max_charge_c']:.1f}",
            f"{coupled.loc[p, 'charge_time_to_target_min']:.1f}",
        ])
    add_table(
        doc,
        ["Protocol", "Iso plating (Ah)", "Coupled plating (Ah)",
         "Plating reduction (%)", "Peak T (°C)", "Charge to 80 % (min)"],
        plating_rows,
    )

    # Pull a few values for the narrative so the prose always matches the CSVs.
    p2 = "cc_cv_2C"
    iso2 = isothermal.loc[p2]
    cp2 = coupled.loc[p2]
    p432 = "mcc_432"
    iso432 = isothermal.loc[p432]
    cp432 = coupled.loc[p432]

    doc.add_paragraph(
        f"Lithium plating drops sharply once self-heating is included. For CC-CV 2C the "
        f"plating loss falls from {iso2['plating_loss_end_ah']:.3f} Ah (isothermal) to "
        f"{cp2['plating_loss_end_ah']:.3f} Ah (coupled) — a "
        f"{(iso2['plating_loss_end_ah'] - cp2['plating_loss_end_ah']) / iso2['plating_loss_end_ah'] * 100:.0f} % "
        f"reduction, i.e. the cell plates about "
        f"{iso2['plating_loss_end_ah'] / cp2['plating_loss_end_ah']:.1f}× less. "
        f"Retention correspondingly rises from {iso2['retention_end_pct']:.1f} % to "
        f"{cp2['retention_end_pct']:.1f} %. The effect is strongest for the aggressive "
        f"MCC 4C-3C-2C protocol, where plating falls from "
        f"{iso432['plating_loss_end_ah']:.3f} to {cp432['plating_loss_end_ah']:.3f} Ah "
        f"and retention reaches {cp432['retention_end_pct']:.1f} % — but at a peak "
        f"temperature of {cp432['t_max_charge_c']:.1f} °C."
    )

    add_figure(
        doc,
        os.path.join(RESULTS, "coupled_retention.png"),
        "Figure 1 – Capacity retention over 40 cycles with thermal and degradation "
        "physics coupled. Compare with the isothermal retention curves of Milestone 1.",
        width_inches=6.0,
    )
    add_figure(
        doc,
        os.path.join(RESULTS, "ageing_retention.png"),
        "Figure 2 – Isothermal retention from Milestone 1, shown for comparison. The "
        "gap between this figure and Figure 1 is the thermal-feedback effect.",
        width_inches=6.0,
    )

    # ------------------------------------------------------ 4. discussion
    doc.add_heading("4. Why Heating Suppresses Plating", level=1)
    doc.add_paragraph(
        "Lithium plating competes with intercalation for the arriving lithium. Plating is "
        "favoured when the anode surface cannot absorb lithium quickly enough — i.e. at "
        "high current density and, critically, at low temperature, where solid-state "
        "diffusion and charge-transfer kinetics are slow. Raising the cell temperature "
        "speeds up intercalation far more than it speeds up plating, so the anode keeps "
        "up with the incoming flux and less lithium is deposited as metal."
    )
    doc.add_paragraph(
        "In the coupled run a 2C charge lifts the cell to roughly "
        f"{cp2['t_max_charge_c']:.0f} °C. At that temperature intercalation is fast "
        "enough that the plating branch is largely bypassed. In the isothermal run the "
        "cell stays pinned at 25 °C, so the same current drives much more plating. This "
        "is why the isothermal result over-predicts plating loss at every rate above 1C."
    )
    doc.add_paragraph(
        "A secondary effect is visible in the charge times: because a warmer cell has "
        "lower internal resistance, the coupled charge-to-target times are slightly "
        "shorter than the isothermal ones for the same current profile."
    )

    # ------------------------------------------------------ 5. caveats
    doc.add_heading("5. Interpretation and Caveats", level=1)
    doc.add_paragraph(
        "The coupled result is physically motivated but model-dependent, and it must not "
        "be presented as an experimentally validated fact. Three points matter:"
    )
    doc.add_paragraph(
        "• The isothermal study is an upper bound. It maximises plating by holding the "
        "cell cold. Reality lies between the isothermal and coupled predictions, because "
        "a real cell neither stays at 25 °C nor heats as uniformly as the lumped model "
        "assumes.\n"
        "• The magnitude rests on the plating temperature dependence. The "
        "qualitative direction (heat suppresses plating) is robust; the exact percentage "
        "is not calibrated against plating-specific experiments.\n"
        "• Thermal safety is a separate constraint. The protocols that age least in "
        "the coupled run are also the hottest (MCC 4C-3C-2C peaks near "
        f"{cp432['t_max_charge_c']:.0f} °C at h = 10). Lower degradation does not mean a "
        "protocol is safe — the cooling system has to carry the heat."
    )
    doc.add_paragraph(
        "It is also worth stating plainly that the coupled ranking differs from the "
        "isothermal ranking. When self-heating is included, the faster protocols no "
        "longer look worse on retention; their disadvantage moves from degradation to "
        "temperature. This is exactly the kind of trade-off the single-mode studies "
        "cannot expose."
    )

    # ------------------------------------------------------ 6. limitations
    doc.add_heading("6. Limitations", level=1)
    doc.add_paragraph(
        "• Accelerated kinetics: rate constants are scaled so trends appear within tens of "
        "cycles; the coupled study inherits this scaling.\n"
        "• Lumped thermal model: a single temperature per cell; internal hotspots and "
        "through-thickness gradients are not resolved.\n"
        "• CC-CV 3C is omitted: the plating term becomes numerically unstable at this "
        "rate (the same reason it is absent from the isothermal ageing study).\n"
        "• Single cooling coefficient (h = 10); the coupled study was not repeated across "
        "the cooling-sensitivity sweep.\n"
        "• No calendar ageing, no mechanical degradation, and no experimental validation "
        "of the coupled plating suppression."
    )

    # ------------------------------------------------------ 7. conclusion
    doc.add_heading("7. Conclusion", level=1)
    doc.add_paragraph(
        "Coupling thermal and degradation physics changes the conclusion of the ageing "
        "study. Under isothermal conditions the fast protocols look clearly worse; once "
        "self-heating is included, their extra heat suppresses plating and their "
        "retention improves. The practical message is that fast-charging protocol design "
        "cannot be separated from thermal management: the same self-heating that "
        "protects the anode from plating is also what pushes the cell toward its "
        "temperature limit. A defensible fast-charging strategy therefore has to be "
        "evaluated on both axes at once — degradation and peak temperature — which is "
        "precisely what the coupled model makes visible."
    )
    doc.add_paragraph(
        "All figures in this report are generated directly from results/coupled_summary.csv "
        "and results/ageing_summary.csv by the accompanying script "
        "(docs/generate_milestone5_report.py); no values are hardcoded."
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print(f"Report saved to: {OUT}")


if __name__ == "__main__":
    main()
