"""Charging protocols compared in the study.

A protocol is a list of PyBaMM experiment steps.  A full cycle is built by
prepending a 1C discharge and appending a short rest (see cycle_steps).
"""

DISCHARGE = "Discharge at 1C until 3.0 V"
REST = "Rest for 2 minutes"
# Constant-voltage tail: standard 0.5 C (2.5 A for a 5 Ah cell) cut-off — long
# enough to capture the tail kinetics without dominating the total charge time.
CV_TAIL = "Hold at 4.2 V until 0.5 A"

PROTOCOLS = {
    "cc_cv_1C": {
        "label": "CC-CV 1C (baseline)",
        "steps": ["Charge at 1C until 4.2 V", CV_TAIL],
    },
    "cc_cv_2C": {
        "label": "CC-CV 2C",
        "steps": ["Charge at 2C until 4.2 V", CV_TAIL],
    },
    "cc_cv_3C": {
        "label": "CC-CV 3C",
        "steps": ["Charge at 3C until 4.2 V", CV_TAIL],
    },
    "boost_4C": {
        "label": "Boost 4C -> 2C",
        "steps": ["Charge at 4C until 4.0 V", "Charge at 2C until 4.2 V", CV_TAIL],
    },
    "mcc_21": {
        "label": "MCC 2C-1C",
        "steps": ["Charge at 2C until 4.1 V", "Charge at 1C until 4.2 V", CV_TAIL],
    },
    "mcc_432": {
        "label": "MCC 4C-3C-2C",
        "steps": ["Charge at 4C until 4.0 V", "Charge at 3C until 4.1 V",
                  "Charge at 2C until 4.2 V", CV_TAIL],
    },
    "mcc_321": {
        "label": "MCC 3C-2C-1C",
        "steps": ["Charge at 3C until 4.0 V", "Charge at 2C until 4.1 V",
                  "Charge at 1C until 4.2 V", CV_TAIL],
    },
}

# A pure 3C CC step to 4.2 V is numerically unstable once plating is enabled
# (the plating overpotential trips the upper cut-off almost immediately), so
# the ageing study skips it.
AGEING_PROTOCOLS = ["cc_cv_1C", "cc_cv_2C", "boost_4C", "mcc_21", "mcc_432", "mcc_321"]
THERMAL_PROTOCOLS = list(PROTOCOLS)


def cycle_steps(key):
    """Full cycle (tuple) for a protocol key: discharge, charge..., rest."""
    return tuple([DISCHARGE] + PROTOCOLS[key]["steps"] + [REST])


def pybamm_experiment(keys, cycles):
    """Experiment with `cycles` repeats for every protocol key.

    Steps of one cycle must be grouped in a tuple, otherwise PyBaMM treats
    every step as a separate cycle.
    """
    import pybamm
    steps = []
    for key in keys:
        steps += [cycle_steps(key)] * cycles
    return pybamm.Experiment(steps)
