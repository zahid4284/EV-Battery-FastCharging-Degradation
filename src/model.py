"""Model and parameter sets used throughout the study.

Three modes are provided:

* ``ageing``  - isothermal 25 degC, SEI growth + irreversible lithium plating.
  Holding temperature constant isolates the effect of the charging current on
  degradation (otherwise strong self-heating at high C-rate suppresses plating
  and hides the trend).
* ``thermal`` - lumped thermal model without degradation, used to quantify the
  temperature penalty of each protocol.
* ``coupled`` - lumped thermal model *with* degradation.  Self-heating and
  ambient cooling feed back into the cell temperature, which in turn modulates
  plating and SEI kinetics.  This is the physically most realistic mode.
"""

import pybamm

# Degradation kinetics are accelerated (relative to the OKane2022 calibration)
# so that end-of-life trends appear within a few hundred cycles.  The ranking
# between protocols is preserved; absolute cycle numbers are not.
AGEING_PARAMETERS = {
    "Ambient temperature [K]": 298.15,
    "Initial temperature [K]": 298.15,
    "Absolute tolerance": 1e-5,
    "SEI kinetic rate constant [m.s-1]": 1e-15,
    "Lithium plating kinetic rate constant [m.s-1]": 1e-10,
}

THERMAL_PARAMETERS = {
    "Ambient temperature [K]": 298.15,
    "Initial temperature [K]": 298.15,
    "Total heat transfer coefficient [W.m-2.K-1]": 10.0,
    "Absolute tolerance": 1e-5,
}

# Coupled mode: thermal + degradation share the same accelerated kinetics as
# the ageing study, plus the same lumped-cell heat-transfer coefficient as the
# thermal study (h = 10 W m-2 K-1, natural-convection level).
COUPLED_PARAMETERS = {
    "Ambient temperature [K]": 298.15,
    "Initial temperature [K]": 298.15,
    "Total heat transfer coefficient [W.m-2.K-1]": 10.0,
    "Absolute tolerance": 1e-5,
    "SEI kinetic rate constant [m.s-1]": 1e-15,
    "Lithium plating kinetic rate constant [m.s-1]": 1e-10,
}


def build_model(mode="ageing"):
    """Return (model, parameter_values) for the requested study mode."""
    if mode == "ageing":
        options = {"thermal": "isothermal",
                   "SEI": "ec reaction limited",
                   "lithium plating": "irreversible"}
        overrides = AGEING_PARAMETERS
    elif mode == "thermal":
        options = {"thermal": "lumped"}
        overrides = THERMAL_PARAMETERS
    elif mode == "coupled":
        options = {"thermal": "lumped",
                   "SEI": "ec reaction limited",
                   "lithium plating": "irreversible"}
        overrides = COUPLED_PARAMETERS
    else:
        raise ValueError(f"Unknown mode: {mode}")

    model = pybamm.lithium_ion.SPMe(options)
    params = pybamm.ParameterValues("OKane2022")
    params.update(overrides)
    return model, params
