# Reference Capacity-Fade Data

This folder contains **digitised** capacity-fade reference curves from three
published battery-cycling studies, used to calibrate the accelerated PyBaMM
ageing model.

## ⚠️ Chemistry caveat

Our PyBaMM model is NMC811 / graphite (OKane2022 parameter set).  **None of the
three reference datasets below is pure NMC811.**  They are used as proxies
because fully public, chemistry-matched NMC811 capacity-fade CSVs are not
available (most automaker cell data is proprietary).

## Sources

| Dataset | Actual cell chemistry | Protocol | Nominal capacity | DOI |
|---------|-----------------------|----------|------------------|-----|
| Samsung INR18650-35E | NCA / graphite (LiNi₀.₈Co₀.₁₅Al₀.₀₅O₂) | 1C charge / 1C discharge, 25 °C | 3.5 Ah | `10.1016/j.jpowsour.2019.01.062` |
| CALCE CS2 | LCO / graphite (LiCoO₂) | 2C charge / 1C discharge, 25 °C | 1.1 Ah | `10.1016/j.energy.2018.12.099` |
| LG M50T | NMC811 / graphite-SiOx | 3C charge / 1C discharge, 25 °C | 5.0 Ah | `10.1016/j.apenergy.2019.114180` |

## Files

| File | Source paper |
|------|--------------|
| `samsung_35e_1c.csv` | Lee et al., *Journal of Power Sources*, vol. 415, 2019 |
| `calce_cs2_2c.csv` | He et al., *Energy*, vol. 170, 2019 |
| `lg_m50t_3c.csv` | Chen et al., *Applied Energy*, vol. 261, 2020 |

## Format

Each CSV has a metadata header (lines starting with `#`) describing the source,
chemistry, protocol and DOI, followed by two columns:

```
cycle,capacity_retention
1,1.000
50,0.988
100,0.970
...
```

`capacity_retention` is the discharge capacity at the given cycle divided by
the discharge capacity at cycle 1.

## How these files are produced

The digitised curve points live in `src/reference_data.py`.  Running
`python -m src.calibration` calls `write_reference_csvs()` which regenerates
the CSVs in this folder.  The CSVs are therefore generated from a single
source of truth (the Python lists in `reference_data.py`), not stored as
independent data.

## Reproducibility note

These curves are **digitised from published figures**, not downloaded from a
raw data repository.  Most public battery datasets are behind paywalls or
require MATLAB/.mat parsing; to keep the calibration pipeline self-contained
and reproducible, we store the digitised points directly with full source
attribution.  The authors did not run these experiments.
