"""Calibrate the accelerated ageing model against real-world battery data.

Our PyBaMM SPMe NMC811 model uses intentionally accelerated SEI and plating
rate constants so that end-of-life trends appear within ~40–80 simulated
cycles.  This script estimates the correspondence between simulated and
real-world cycle counts by fitting the simulated capacity-fade curve to three
published NMC capacity-fade datasets.

Reference data
--------------
All three datasets are for NMC-based lithium-ion cells (matching our model
chemistry).  Each is cited with DOI and source; digitised retention curves
live in ``data/*.csv`` (written by ``src/reference_data.write_reference_csvs``):

  Samsung_35E_1C — NMC811/graphite, 1C/1C @ 25 °C
  CALCE_CS2_2C   — NMC111/graphite, 2C/1C @ 25 °C
  LG_M50T_3C     — NMC811/graphite-SiOx, 3C/1C @ 25 °C

Usage
-----
    python -m src.calibration                  # default
    python -m src.calibration --outdir results
"""

import argparse
import csv
import os
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import model as model_mod
from . import simulate as sim_mod
from .reference_data import REFERENCE_DATASETS, write_reference_csvs


def load_reference_csv(path):
    """Load a reference capacity-fade CSV, skipping header lines."""
    rows = []
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            try:
                cycle = int(row[0])
                retention = float(row[1])
            except ValueError:
                # header row "cycle,capacity_retention" — skip
                continue
            rows.append((cycle, retention))
    return np.array(rows, dtype=float)


def simulate_retention_per_protocol(protocol_key, cycles=80):
    """Run an ageing simulation and return (cycle_numbers, retention_fractions).

    We rebuild the model on every call so there is no module-level state
    mutation — the function is self-contained and safe to call repeatedly.
    """
    m, p = model_mod.build_model("ageing")
    rows, _ = sim_mod.run_protocol(
        protocol_key, cycles, mode="ageing",
        solver=sim_mod.make_solver(), model_override=(m, p))

    cycle_nums = np.array([r["cycle"] for r in rows], dtype=float)
    q0 = rows[0]["discharge_capacity_ah"]
    retentions = np.array([r["discharge_capacity_ah"] / q0 for r in rows])
    return cycle_nums, retentions


def best_fit_scale_factor(simulated_cycles, simulated_retentions,
                          reference_data):
    """Find the scaling factor that maps the simulated cycle axis onto the
    reference data so that the two curves align best in a least-squares sense.

    Returns (scale, rmse) where scale = real_cycle / simulated_cycle.
    """
    ref_cycles = reference_data[:, 0]
    ref_ret = reference_data[:, 1]

    best_scale, best_rmse = None, float("inf")
    for scale in np.logspace(-0.5, 2.5, 120):
        sim_cycles_real = simulated_cycles * scale
        mask = (sim_cycles_real >= ref_cycles[0]) & (sim_cycles_real <= ref_cycles[-1])
        if np.sum(mask) < 3:
            continue
        interp_ret = np.interp(ref_cycles, sim_cycles_real, simulated_retentions,
                               left=np.nan, right=np.nan)
        valid = ~np.isnan(interp_ret)
        if np.sum(valid) < 3:
            continue
        rmse = np.sqrt(np.mean((ref_ret[valid] - interp_ret[valid]) ** 2))
        if rmse < best_rmse:
            best_rmse = rmse
            best_scale = scale

    return best_scale, best_rmse


def run_calibration(outdir="results", datadir="data"):
    """Run calibration across all reference datasets and simulated protocols."""
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(datadir, exist_ok=True)

    # Ensure reference CSVs exist
    write_reference_csvs(datadir)

    # Simulate 80 cycles for each protocol
    protocols = ["cc_cv_1C", "cc_cv_2C", "boost_4C", "mcc_21"]

    print("\n" + "=" * 64)
    print("Calibration: accelerated NMC ageing ↔ published NMC capacity fade")
    print("=" * 64)

    # ---- Step 1: collect simulated retention curves ----
    sim_curves = {}
    for p in protocols:
        cyc, ret = simulate_retention_per_protocol(p, cycles=80)
        sim_curves[p] = (cyc, ret)

    # ---- Step 2: fit scaling to each reference dataset ----
    calibration_results = []
    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    print(f"\n{'Dataset':<18} {'Protocol':<12} {'Scale':<10} {'RMSE':<10}")
    print("-" * 52)
    for idx, (ds_name, meta) in enumerate(REFERENCE_DATASETS.items()):
        csv_path = os.path.join(datadir, f"{ds_name.lower()}.csv")
        ref_data = load_reference_csv(csv_path)
        best_protocol, best_scale, best_rmse = None, None, float("inf")
        for p in protocols:
            cyc, ret = sim_curves[p]
            scale, rmse = best_fit_scale_factor(cyc, ret, ref_data)
            if scale is None:
                continue
            print(f"{ds_name:<18} {p:<12} {scale:<10.1f} {rmse:<10.4f}")
            if rmse < best_rmse:
                best_rmse, best_scale, best_protocol = rmse, scale, p
        calibration_results.append({
            "dataset": ds_name,
            "description": (f"{meta['chemistry']}, {meta['charge_rate']} charge / "
                            f"{meta['discharge_rate']} discharge @ "
                            f"{meta['temperature_c']} degC"),
            "cycles_to_80pct_real": meta["cycles_to_80pct"],
            "doi": meta["doi"],
            "source": meta["source"],
            "best_protocol": best_protocol,
            "scale": best_scale,
            "rmse": best_rmse,
            "scale_range_real": f"{80*best_scale:.0f} real cycles ≈ 80 sim cycles",
        })

    # ---- Step 3: Plot simulated vs real (best fit) ----
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)

    for ax, (ds_name, meta) in zip(axes, REFERENCE_DATASETS.items()):
        csv_path = os.path.join(datadir, f"{ds_name.lower()}.csv")
        ref_data = load_reference_csv(csv_path)
        color = colors[list(REFERENCE_DATASETS).index(ds_name) % len(colors)]

        ax.plot(ref_data[:, 0], ref_data[:, 1], "o-", color=color, markersize=4,
                label=f"Real: {ds_name}")

        best_p = next(r["best_protocol"] for r in calibration_results
                      if r["dataset"] == ds_name)
        best_scale = next(r["scale"] for r in calibration_results
                          if r["dataset"] == ds_name)

        for p, (cyc, ret) in sim_curves.items():
            scaled_cyc = cyc * best_scale
            ls = "-" if p == best_p else "--"
            alpha = 1.0 if p == best_p else 0.4
            lw = 2.2 if p == best_p else 1.2
            ax.plot(scaled_cyc, ret, ls, alpha=alpha, lw=lw,
                    label=f"Sim: {p} ({scaled_cyc[-1]:.0f} cyc)")

        ax.set_xlabel("Real-world cycle number")
        ax.set_title(f"{ds_name} (best ≈ {best_scale:.0f}×)")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, max(ref_data[:, 0]) * 1.1)

    axes[0].set_ylabel("Capacity retention")
    axes[0].legend(fontsize=7, loc="lower left")

    fig.suptitle("Calibration: simulated accelerated ageing ↔ published NMC capacity fade",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "calibration.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nPlot saved → {outdir}/calibration.png")

    # ---- Step 4: Summary ----
    print("\n" + "=" * 64)
    print("Calibration summary")
    print("=" * 64)
    print(f"{'Dataset':<22} {'Best match':<12} {'Scale':<8} {'RMSE':<10} {'DOI':<18}")
    for r in calibration_results:
        print(f"{r['dataset']:<22} {r['best_protocol']:<12} "
              f"{r['scale']:<8.1f} {r['rmse']:<10.4f} {r['doi']:<18}")

    summary_path = os.path.join(outdir, "calibration_summary.json")
    with open(summary_path, "w") as f:
        json.dump(calibration_results, f, indent=2)
    print(f"\nSummary saved → {summary_path}")

    return calibration_results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default="results")
    parser.add_argument("--datadir", default="data")
    args = parser.parse_args()
    run_calibration(outdir=args.outdir, datadir=args.datadir)


if __name__ == "__main__":
    main()
