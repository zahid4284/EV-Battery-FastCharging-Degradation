# Setup

## 1. Python

Use Python **3.11** (3.10–3.12 are also fine). PyBaMM does not yet have wheels
for every 3.13/3.14 release, so older interpreters avoid source builds.

```bash
python --version
```

## 2. Virtual environment

```bash
cd EV-Battery-FastCharging-Degradation
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

## 3. Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

PyBaMM pulls in CasADi and SciPy; the first install takes several minutes.

## 4. Verify

```bash
python -c "import pybamm; print(pybamm.__version__)"
python run_experiment.py --cycles 3 --mode thermal
python -m pytest tests -q
```

A full run of both studies with the default 40 cycles takes roughly 2–4 minutes
on a modern laptop.

---

## Troubleshooting

**`IDA_ERR_FAIL` / `corrector convergence failed`**

The degradation model is stiff. `src/model.py` already sets
`Absolute tolerance = 1e-5`. If a run still fails, lower the C-rate of the
failing protocol, or add `"Lower voltage cut-off [V]": 2.5` to the parameter
dictionary. Never "fix" it by removing the thermal model — that changes the
physics.

**`KeyError: 'Parameter ... not found'`**

You are probably using the default (`Chen2020`) parameter set instead of
`OKane2022`. Lithium plating parameters only exist in the degradation
parameter sets. The code already selects the right one.

**`'Solution' object has no attribute 'summary'`**

The summary API changed between PyBaMM releases. This repository deliberately
does **not** use `solution.summary`: every metric is computed from
`solution.cycles[i]` and named variables, which is stable across versions.

**Plots show a sawtooth instead of a smooth curve**

Spatially resolved variables are stored as `(space, time)` in `entries`.
`src/metrics.py::temperature_series` reshapes to `(-1, n_times)` before taking
the maximum. If you add a new variable, re-use that helper.

**Matplotlib complains about a display**

All figures use the `Agg` backend (`src/plots.py`), so no display is required.

**Windows long-path errors**

Enable long paths, or clone the repository into a short directory such as
`C:\work\fastcharge`.
