# Hands-on roadmap

The code in this repository is a working baseline. The value for your
application comes from the parts **you** change, break and explain. Work
through the milestones in order and keep a short note after each one — those
notes become the *results and discussion* section of your report, and talking
points in an interview.

---

## Milestone 1 — Reproduce the baseline (1–2 days)

- Install the project following `docs/SETUP.md`.
- Run `python run_experiment.py` and confirm your summary tables match the
  README within ~1 %.
- Open every figure and write one sentence per figure describing the trend.

**Deliverable:** a paragraph explaining why 2C saves ~29 % of charge time but
loses 3.3 percentage points of capacity.

---

## Milestone 2 — Break the model on purpose (2 days)

Do these one at a time and record what happens:

1. Set `Absolute tolerance` to `1e-8` in `src/model.py`. Does the runtime
   explode? Why?
2. Remove the thermal model (use `{"thermal": "isothermal"}`) in the **thermal**
   study. Which conclusions disappear?
3. Set `Total heat transfer coefficient` to `1.0` and then `100.0`. How does
   the peak temperature of the 3C protocol change? Which cooling system does
   the latter correspond to?

**Deliverable:** a table of peak temperature versus heat-transfer coefficient.
This is your first "sensitivity analysis" — exactly what a research supervisor
wants to see.

---

## Milestone 3 — Calibrate the degradation kinetics (3–4 days)

The shipped parameters are inflated to make trends visible in tens of cycles.

1. Read the description of the O'Kane 2022 parameter set in the PyBaMM
   documentation.
2. Find one published capacity-fade curve for an NMC/graphite 18650 or 21700
   cell (e.g. NASA PCoE, Oxford Battery Degradation Dataset).
3. Tune `SEI kinetic rate constant` and `Lithium plating kinetic rate constant`
   so that your 1C baseline reproduces that fade curve over ~200 cycles.
4. Re-run the study with the new parameters and update the README table.

**Deliverable:** before/after retention curves and a short justification of the
parameter values you chose. This is the single most impressive part of the
project — it proves you can fit a physical model to data, not just run it.

---

## Milestone 4 — Add a protocol of your own (2 days)

Design a charging profile that beats `mcc_21` on the Pareto front
(faster *and* at least as durable). Ideas:

- `MCC 2.5C-1.5C-0.5C`
- A temperature-aware step: 3C while T < 40 °C, else 1C
  (hint: requires an experiment with voltage/temperature thresholds)
- A rest-inserted protocol: charge 2C for 10 min, rest 2 min, repeat

Add it to `src/protocols.py`, run both studies, and plot it against the others.

**Deliverable:** the updated Pareto plot with your protocol highlighted.

---

## Milestone 5 — Answer a question the baseline cannot (4–5 days)

Pick one extension and treat it seriously:

| Extension | What you learn |
|---|---|
| Pack-level model (N cells with thermal coupling) | whether one hot cell dominates pack ageing |
| Ambient temperature sweep (0, 25, 45 °C) | cold charging is often worse than hot |
| Sensitivity study (10 parameters, ±50 %) | which parameter controls plating onset |
| Simple MPC controller | closed-loop charging instead of fixed protocols |

**Deliverable:** a 2–3 page report with figures, and one clear conclusion stated
in a single sentence.

---

## Milestone 6 — Publish (1 day)

- Write the README results section with the tables produced in Milestone 3.
- Add a `docs/RESULTS.md` with one figure per finding.
- Push to GitHub with a clear commit history (one commit per milestone).
- Mention the repository in your CV and SOP: *"Implemented a PyBaMM-based
  fast-charging study; calibrated degradation kinetics against published fade
  data and identified a protocol that reduces charge time by X % for Y pp of
  capacity loss."*

That sentence, backed by a public repository, is worth more than any
certificate.
