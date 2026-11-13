"""Main entry point: run charging protocols, save metrics and figures.

Modes
-----
ageing  : isothermal 25 degC, SEI + lithium plating (degradation only)
thermal : lumped thermal model, no degradation (heat only)
coupled : lumped thermal model *with* degradation (EC-thermal-SEI-plating coupled)
pack    : 96-cell pack thermal simulation
cooling : thermal sensitivity h = 1, 10, 100 W m⁻² K⁻¹
all     : ageing + thermal + coupled + cooling + pack

Usage
-----
    python run_experiment.py --mode ageing          # baseline 40-cycle study
    python run_experiment.py --mode thermal         # thermal-only
    python run_experiment.py --mode coupled         # EC-thermal-degradation
    python run_experiment.py --mode pack            # 96-cell pack
    python run_experiment.py --mode cooling         # h sensitivity
    python run_experiment.py --mode all             # everything
    python run_experiment.py --cycles 10            # quick smoke test
    python run_experiment.py --protocols cc_cv_1C,mcc_432
"""

import argparse
import os

import pandas as pd

from src import plots, protocols, simulate


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",
                        choices=["ageing", "thermal", "coupled", "pack",
                                 "cooling", "all"],
                        default="ageing")
    parser.add_argument("--cycles", type=int, default=40,
                        help="cycles per protocol (default 40)")
    parser.add_argument("--protocols", type=str, default="",
                        help="comma separated protocol keys (default: all)")
    parser.add_argument("--outdir", type=str, default="results")
    return parser.parse_args()


def collect(keys, cycles, mode, solver):
    rows, profiles = [], {}
    for key in keys:
        protocol_rows, profile = simulate.run_protocol(
            key, cycles, mode=mode, solver=solver)
        rows += protocol_rows
        profiles[key] = profile
    return pd.DataFrame(rows), profiles


def summarise(cycles_df, keys):
    records = []
    for key in keys:
        group = cycles_df[cycles_df["protocol"] == key]
        first, last = group.iloc[0], group.iloc[-1]
        records.append({
            "protocol": key,
            "label": first["label"],
            "cycles": len(group),
            "charge_time_to_target_min": round(first["charge_time_to_target_min"], 1),
            "charge_time_full_min": round(first["charge_time_full_min"], 1),
            "t_max_charge_c": round(group["t_max_charge_c"].max(), 1),
            "retention_end_pct": round(
                100 * last["discharge_capacity_ah"] / first["discharge_capacity_ah"], 1),
            "sei_loss_end_ah": round(last["sei_loss_ah"], 4),
            "plating_loss_end_ah": round(last["plating_loss_ah"], 4),
        })
    return pd.DataFrame(records)


def save_profiles(profiles, outdir, filename):
    frames = [pd.DataFrame({"protocol": key,
                            "label": protocols.PROTOCOLS[key]["label"],
                            "time_min": time_min,
                            "temperature_c": temp})
              for key, (time_min, temp) in profiles.items()]
    pd.concat(frames).to_csv(os.path.join(outdir, filename), index=False)


def run_ageing_study(cycles, outdir, solver):
    """Isothermal ageing study — SEI + plating at 25 °C."""
    print("\n=== Ageing study (isothermal 25 degC, SEI + plating) ===")
    df, profiles = collect(protocols.AGEING_PROTOCOLS, cycles, "ageing", solver)
    summary = summarise(df, protocols.AGEING_PROTOCOLS)
    df.to_csv(os.path.join(outdir, "ageing_cycles.csv"), index=False)
    summary.to_csv(os.path.join(outdir, "ageing_summary.csv"), index=False)
    save_profiles(profiles, outdir, "ageing_first_charge.csv")

    plots.plot_retention(df, outdir)
    plots.plot_pareto(summary, outdir)
    plots.plot_charge_time(summary, outdir)
    plots.plot_degradation_modes(summary, outdir)

    print(summary.to_string(index=False))
    return summary


def run_thermal_study(outdir, solver):
    """Thermal-only study — lumped h = 10 W m⁻² K⁻¹, two cycles per protocol."""
    print("\n=== Thermal study (lumped h = 10 W m⁻² K⁻¹, no degradation) ===")
    df, profiles = collect(protocols.THERMAL_PROTOCOLS, 2, "thermal", solver)
    summary = summarise(df, protocols.THERMAL_PROTOCOLS)
    df.to_csv(os.path.join(outdir, "thermal_cycles.csv"), index=False)
    summary.to_csv(os.path.join(outdir, "thermal_summary.csv"), index=False)
    save_profiles(profiles, outdir, "thermal_first_charge.csv")

    plots.plot_peak_temperature_bar(summary, outdir)
    plots.plot_first_charge_profile(profiles, outdir)
    plots.plot_temperature(df, outdir)

    print(summary.to_string(index=False))
    return summary


def run_coupled_study(cycles, outdir, solver):
    """Coupled EC-thermal-degradation — lumped h = 10 + SEI + plating."""
    print("\n=== Coupled EC-thermal-degradation (lumped h = 10 W m⁻² K⁻¹ + SEI + plating) ===")
    df, profiles = collect(protocols.AGEING_PROTOCOLS, cycles, "coupled", solver)
    summary = summarise(df, protocols.AGEING_PROTOCOLS)
    df.to_csv(os.path.join(outdir, "coupled_cycles.csv"), index=False)
    summary.to_csv(os.path.join(outdir, "coupled_summary.csv"), index=False)
    save_profiles(profiles, outdir, "coupled_first_charge.csv")

    # Save to a DIFFERENT filename so --mode all doesn't overwrite ageing's plot
    plots.plot_retention(df, outdir, fname="coupled_retention.png")

    print(summary.to_string(index=False))
    return summary


def run_cooling_study(outdir, solver):
    """Thermal sensitivity — h = 1, 10, 100 W m⁻² K⁻¹ for every thermal protocol."""
    import pybamm
    print("\n=== Cooling sensitivity (h = 1, 10, 100 W m⁻² K⁻¹) ===")
    from src import model
    h_values = [1.0, 10.0, 100.0]
    all_rows = []
    # Use Casadi safe solver for h=100 — IDAKLU is numerically unstable there
    safe_solver = pybamm.CasadiSolver(mode="safe", dt_max=30)
    for h in h_values:
        print(f"  h = {h} W m⁻² K⁻¹")
        overrides = model.THERMAL_PARAMETERS.copy()
        overrides["Total heat transfer coefficient [W.m-2.K-1]"] = h
        m, p = model.build_model("thermal")
        p.update(overrides)
        rows = []
        for key in protocols.THERMAL_PROTOCOLS:
            proto_rows, _ = simulate.run_protocol(
                key, 2, mode="thermal", solver=safe_solver,
                model_override=(m, p))
            for r in proto_rows:
                r = dict(r)
                r["h_wm2k"] = h
                rows.append(r)
        all_rows.extend(rows)
    df = pd.DataFrame(all_rows)
    df.to_csv(os.path.join(outdir, "cooling_sensitivity.csv"), index=False)
    records = []
    for h in h_values:
        g = df[df["h_wm2k"] == h]
        for key in protocols.THERMAL_PROTOCOLS:
            pg = g[g["protocol"] == key]
            records.append({
                "h_wm2k": h,
                "protocol": key,
                "label": pg.iloc[0]["label"],
                "t_max_charge_c": round(pg["t_max_charge_c"].max(), 1),
            })
    summary = pd.DataFrame(records)
    summary.to_csv(os.path.join(outdir, "cooling_summary.csv"), index=False)
    print(summary.to_string(index=False))
    return summary


def run_pack(outdir):
    """96-cell pack thermal simulation."""
    from src import pack
    print("\n=== 96-cell pack thermal simulation ===")
    pack.run_pack_study(outdir=outdir, cooling_h=10.0)
    pack.run_pack_study(outdir="results_pack_h100", cooling_h=100.0)


def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    solver = simulate.make_solver()

    mode = args.mode

    if mode in ("ageing", "all"):
        run_ageing_study(args.cycles, args.outdir, solver)
    if mode in ("thermal", "all"):
        run_thermal_study(args.outdir, solver)
    if mode in ("coupled", "all"):
        run_coupled_study(args.cycles, args.outdir, solver)
    if mode in ("cooling", "all"):
        run_cooling_study(args.outdir, solver)
    if mode in ("pack", "all"):
        run_pack(args.outdir)

    print(f"\nDone. Results in {args.outdir}/")


if __name__ == "__main__":
    main()
