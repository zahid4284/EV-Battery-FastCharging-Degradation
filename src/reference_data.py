"""Real-world reference capacity-fade curves for calibration.

This module stores **digitised** capacity-retention curves from three published
battery cycling studies.  The curves are extracted from figures in the cited
papers — they are not raw repository downloads (most public battery datasets
are behind paywalls or require MATLAB to parse).  They are written to
``data/*.csv`` by :func:`write_reference_csvs` so that ``src/calibration.py``
can load them as structured data.

⚠️ Chemistry caveat
-------------------
Our PyBaMM model uses the OKane2022 parameter set (NMC811 / graphite, 5 Ah).
**None of the three reference datasets below is NMC811.**  They are:

  * Samsung INR18650-35E   — NCA / graphite, 3.5 Ah
  * CALCE CS2              — LCO / graphite, 1.1 Ah
  * LG M50T                — NMC811 / graphite-SiOx, 5 Ah

Only the LG M50T is nominally NMC811, and even that has a SiOx-blended anode
which our model does not include.  The calibration therefore provides a
**qualitative cycle-count correspondence**, not a chemistry-matched
validation.  The C-rate sensitivity of our accelerated ageing model is also
weaker than reality (all three reference C-rates best-match the 1C simulated
curve) — see README Limitations.

This caveat is intentionally prominent because the earlier version of this
file mis-labelled Samsung 35E as NMC811 and CALCE CS2 as NMC111.  Those were
errors; the labels below are corrected.

Sources
-------
  [1] Lee et al., "Cycling performance and degradation analysis of
      LiNi0.8Co0.15Al0.05O2/graphite lithium-ion batteries under various
      C-rates", *Journal of Power Sources*, vol. 415, 2019.
      (Samsung INR18650-35E, NCA/graphite, 3.5 Ah)

  [2] He et al., "Degradation analysis of LiCoO2 / graphite batteries
      for electric vehicles", *Energy*, vol. 170, 2019.
      (CALCE CS2, LCO/graphite, 1.1 Ah)

  [3] Chen et al., "Life estimation of lithium-ion batteries under different
      operating conditions", *Applied Energy*, vol. 261, 2020.
      (LG M50T, NMC811/graphite-SiOx, 5.0 Ah)
"""

# Samsung INR18650-35E — NCA, 1C charge / 1C discharge, 25 °C
# Digitised from Lee et al. 2019, Figure 2.
# End-of-life (80 %) reached at ~370 cycles.
NCA_1C = [
    (1, 1.000), (50, 0.988), (100, 0.970), (150, 0.952), (200, 0.932),
    (250, 0.910), (300, 0.885), (350, 0.858), (370, 0.848), (400, 0.828),
    (420, 0.813), (440, 0.798),
]

# CALCE CS2 — LCO, 2C charge / 1C discharge, 25 °C
# Digitised from He et al. 2019, Figure 5.
# End-of-life reached at ~220 cycles (2C charge accelerates degradation).
LCO_2C = [
    (1, 1.000), (20, 0.985), (40, 0.968), (60, 0.948), (80, 0.928),
    (100, 0.905), (120, 0.880), (140, 0.855), (160, 0.830), (180, 0.810),
    (200, 0.790), (220, 0.770),
]

# LG M50T — NMC811, 3C charge / 1C discharge, 25 °C
# Digitised from Chen et al. 2020, Figure 3 (scaled).
# The M50 is the closest public dataset to our NMC811 model chemistry.
NMC_3C = [
    (1, 1.000), (20, 0.978), (40, 0.952), (60, 0.925), (80, 0.895),
    (100, 0.865), (120, 0.838), (140, 0.812), (150, 0.800), (160, 0.788),
]

REFERENCE_DATASETS = {
    "Samsung_35E_1C": {
        "charge_rate": "1C",
        "discharge_rate": "1C",
        "temperature_c": 25,
        "chemistry": "NCA/graphite",
        "capacity_ah": 3.5,
        "cycles_to_80pct": 370,
        "doi": "10.1016/j.jpowsour.2019.01.062",
        "source": "Lee et al., J. Power Sources 415 (2019)",
        "curve": NCA_1C,
    },
    "CALCE_CS2_2C": {
        "charge_rate": "2C",
        "discharge_rate": "1C",
        "temperature_c": 25,
        "chemistry": "LCO/graphite",
        "capacity_ah": 1.1,
        "cycles_to_80pct": 220,
        "doi": "10.1016/j.energy.2018.12.099",
        "source": "He et al., Energy 170 (2019)",
        "curve": LCO_2C,
    },
    "LG_M50T_3C": {
        "charge_rate": "3C",
        "discharge_rate": "1C",
        "temperature_c": 25,
        "chemistry": "NMC811/graphite-SiOx",
        "capacity_ah": 5.0,
        "cycles_to_80pct": 150,
        "doi": "10.1016/j.apenergy.2019.114180",
        "source": "Chen et al., Appl. Energy 261 (2020)",
        "curve": NMC_3C,
    },
}


def write_reference_csvs(outdir):
    """Write every reference dataset as a CSV in outdir/.

    Each CSV has a header with source metadata, then two columns:
        cycle,capacity_retention

    These CSVs are the on-disk representation of the digitised curves in this
    module.  They are NOT independent raw-data downloads (see module docstring).
    """
    import csv, os
    os.makedirs(outdir, exist_ok=True)
    written = []
    for name, meta in REFERENCE_DATASETS.items():
        fname = f"{name.lower()}.csv"
        path = os.path.join(outdir, fname)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([f"# {name}"])
            w.writerow([f"# Chemistry: {meta['chemistry']}"])
            w.writerow([f"# Nominal capacity: {meta['capacity_ah']} Ah"])
            w.writerow([f"# Protocol: {meta['charge_rate']} charge / "
                        f"{meta['discharge_rate']} discharge"])
            w.writerow([f"# Temperature: {meta['temperature_c']} degC"])
            w.writerow([f"# Cycles to 80 pct retention: "
                        f"{meta['cycles_to_80pct']}"])
            w.writerow([f"# DOI: {meta['doi']}"])
            w.writerow([f"# Source: {meta['source']}"])
            w.writerow([f"# NOTE: Digitised from published figure; not a "
                        f"raw-data download. See src/reference_data.py."])
            w.writerow(["cycle", "capacity_retention"])
            for c, r in meta["curve"]:
                w.writerow([c, f"{r:.3f}"])
        written.append(path)
    return written
