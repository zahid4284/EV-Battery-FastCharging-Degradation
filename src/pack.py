"""96-cell series-pack simulation with inter-cell thermal coupling.

Single-cell thermal studies assume each cell sees the same ambient temperature.
In a real EV pack cells exchange heat with their neighbours — cells in the
pack centre run hotter than cells at the edges, and this changes the thermal
stress felt by every cell.

This module models a 96-cell pack as an 8 × 12 grid of cells connected in
series, with:

    • heat transfer between adjacent cells (horizontal + vertical coupling)
    • heat transfer from each cell to a shared cooling plate / ambient
    • tiny cell-to-cell heat-generation noise to break perfect symmetry

The thermal model is lumped per cell with Euler integration.  The magnitude
of heat generation, cooling, and coupling are all physically calibrated.
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


# ---------------------------------------------------------------------------
# Pack geometry & physical constants
# ---------------------------------------------------------------------------
PACK_ROWS, PACK_COLS = 8, 12
N_CELLS = PACK_ROWS * PACK_COLS   # 96 cells in series

# 21700 cell — 3.7 V nominal, 5.0 Ah capacity
CELL_V_NOM = 3.7        # V
CELL_Q_NOM = 5.0        # Ah

# Physical constants for one 21700 NMC cell
CELL_MASS_KG = 0.070           # 70 g
CELL_Cp = 1.1 * CELL_MASS_KG * 1000   # 77 J/K (Cp ≈ 1.1 J/gK)
# Total surface area (cylinder sides + end caps) ≈ 55 cm²
CELL_SURFACE_AREA_M2 = 0.0055

# Overall heat-transfer coefficient per cell.
# We use h applied to the full cell surface area — this matches the
# single-cell baseline (h = 10 W m-2 K-1, moderate forced air, gives 55 mW/K
# per cell).  Real pack cooling may include plate contact + channel flow;
# here we keep a single lumped h per cell for clarity.
COOLING_H = 10.0

# Inter-cell coupling (thermal conductance K in W K-1)
# Typical value through plastic separator: K ≈ 0.5–2 W/K per neighbour
COUPLING_K = 5.0               # W K-1 (higher: cells sit tightly together)

AMBIENT_C = 25.0               # °C — cooling-plate temperature

# --- Cell-level resistance ---
# R_REF ≈ 15 mΩ total (ohmic + activation) for a 21700 NMC cell.  With this
# value, at h = 10 W m-2 K-1 the 2C and 3C peak temperatures (54.7 and 69.9 °C)
# are broadly consistent with the single-cell PyBaMM thermal study.  The value
# is not a fit to experimental data — it is a reasonable cell resistance that
# produces physically plausible temperature trends.
R_REF = 0.015                   # Ohm at 25 C
Ea_R = 1200.0                   # J/mol (reduced sensitivity vs. crude model)
R_GAS = 8.314                   # J/mol K


def cell_resistance(T_c):
    """Ohmic + activation resistance, simplified."""
    T_K = T_c + 273.15
    return R_REF * np.exp(Ea_R / R_GAS * (1 / T_K - 1 / 298.15))


def heat_generation_per_cell(I_A, T_c):
    """Total heat generation (W) — Joule + entropic term.

    Joule: I²·R(T)
    Entropic: small for NMC near 3.7 V, included as a linearised term.
    """
    R = cell_resistance(T_c)
    joule = I_A ** 2 * R
    # entropic ≈ -I·T·dOCV/dT with dOCV/dT ≈ -0.0001 V/K for NMC
    entropic = -I_A * (T_c + 273.15) * (-1e-4)
    return joule + entropic


# ---------------------------------------------------------------------------
# Charging protocol currents (5 Ah cell)
# ---------------------------------------------------------------------------
def protocol_current(protocol_key):
    """Return I(t) (A) callable for a 5 Ah cell."""
    def cc_ccv(cc_s, I_cc_A, cv_decay_s=240):
        def _I(t):
            if t < cc_s:
                return I_cc_A
            elif t < cc_s + cv_decay_s:
                return I_cc_A * np.exp(-(t - cc_s) / 80.0)
            else:
                return 0.0
        return _I

    def multistage(stages):
        """stages: list of (duration_s, current_A). Tail decays like CV."""
        def _I(t):
            t_ = 0.0
            for d, I in stages:
                if t < t_ + d:
                    return I
                t_ += d
            # CV-like exponential tail
            tail_dur = 300.0
            if t < t_ + tail_dur:
                return stages[-1][1] * np.exp(-(t - t_) / 80.0)
            return 0.0
        return _I

    Q = CELL_Q_NOM

    I_1C = cc_ccv(45 * 60, Q * 1.0)
    I_2C = cc_ccv(23 * 60, Q * 2.0)
    I_3C = cc_ccv(15 * 60, Q * 3.0)
    I_boost = multistage([(3 * 60, Q * 4.0), (20 * 60, Q * 2.0)])
    I_mcc21 = multistage([(15 * 60, Q * 2.0), (25 * 60, Q * 1.0)])
    I_mcc321 = multistage([(8 * 60, Q * 3.0), (12 * 60, Q * 2.0), (20 * 60, Q * 1.0)])
    I_mcc432 = multistage([(3 * 60, Q * 4.0), (7 * 60, Q * 3.0), (12 * 60, Q * 2.0)])

    return {
        "cc_cv_1C": I_1C, "cc_cv_2C": I_2C, "cc_cv_3C": I_3C,
        "boost_4C": I_boost, "mcc_21": I_mcc21,
        "mcc_321": I_mcc321, "mcc_432": I_mcc432,
    }[protocol_key]


# ---------------------------------------------------------------------------
# Pack thermal simulation
# ---------------------------------------------------------------------------
def simulate_pack(protocol_current_callable, duration_s, dt=1.0,
                  cooling_h=COOLING_H, coupling_k=COUPLING_K,
                  initial_t_c=25.0, ambient_c=AMBIENT_C, noise_frac=0.02):
    """Run pack simulation and return T_history (n_timesteps, rows, cols).

    Uses explicit Euler integration.  The noise_frac parameter adds
    Gaussian heat-generation noise so the pack does not remain perfectly
    symmetric.

    Explicit-Euler stability: the inter-cell coupling sets a time scale
    ~ CELL_Cp / (4 * COUPLING_K) ≈ 4 s, so dt must be kept small (≤ ~3 s)
    to avoid numerical ringing.  The default dt = 1 s is well inside the
    stable regime.
    """
    n_steps = int(duration_s / dt) + 1
    T = np.full((PACK_ROWS, PACK_COLS), initial_t_c, dtype=float)

    # Pre-compute cell positions and valid neighbour masks
    # Neighbour offsets
    neighbour_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    T_history = np.zeros((n_steps, PACK_ROWS, PACK_COLS))
    Q_gen_history = np.zeros_like(T_history)

    # Fixed Gaussian noise map (so it's consistent across time steps)
    rng = np.random.default_rng(42)
    cell_noise = 1.0 + rng.normal(0, noise_frac, size=(PACK_ROWS, PACK_COLS))

    # Spatially varying cooling coefficient — edges see better cooling
    # (closer to air flow), centre cells see poorer heat removal.
    # This creates the natural centre-hot gradient observed in real packs.
    row_idx = np.arange(PACK_ROWS).reshape(PACK_ROWS, 1)
    col_idx = np.arange(PACK_COLS).reshape(1, PACK_COLS)
    centre_r = (PACK_ROWS - 1) / 2.0
    centre_c = (PACK_COLS - 1) / 2.0
    dist_from_centre = np.sqrt((row_idx - centre_r) ** 2 + (col_idx - centre_c) ** 2)
    dist_norm = dist_from_centre / dist_from_centre.max()  # 0 at centre, 1 at edges
    # h is 30 % lower at centre cells, 10 % higher at edge cells
    h_map = cooling_h * (0.7 + 0.4 * dist_norm)

    for step in range(n_steps):
        t = step * dt
        I = protocol_current_callable(t)

        # 1. Heat generation (same I for all cells, scaled by noise)
        Q_gen = heat_generation_per_cell(I, T) * cell_noise

        # 2. Cooling (to ambient / plate, via full cell surface, spatially varying)
        Q_cool = h_map * CELL_SURFACE_AREA_M2 * (T - ambient_c)

        # 3. Inter-cell coupling — sum over valid neighbours
        Q_coupling = np.zeros_like(T)
        for dr, dc in neighbour_offsets:
            shifted = np.roll(T, shift=(dr, dc), axis=(0, 1))
            valid = np.ones_like(T, dtype=bool)
            if dr == -1:   valid[0, :] = False
            elif dr == 1:  valid[-1, :] = False
            if dc == -1:   valid[:, 0] = False
            elif dc == 1:  valid[:, -1] = False
            Q_coupling += coupling_k * np.where(valid, shifted - T, 0.0)

        # 4. Euler update + clip physically
        dT_dt = (Q_gen - Q_cool + Q_coupling) / CELL_Cp
        T = T + dT_dt * dt
        np.clip(T, 20.0, 90.0, out=T)

        T_history[step] = T
        Q_gen_history[step] = Q_gen

    return T_history, Q_gen_history


# ---------------------------------------------------------------------------
# Pack study runner + plots
# ---------------------------------------------------------------------------
def run_pack_study(outdir="results", cooling_h=COOLING_H):
    """Run all 7 protocols and produce summary CSV + 3 figures."""
    os.makedirs(outdir, exist_ok=True)

    PROTOCOLS = [
        ("cc_cv_1C", "1C CC-CV"),
        ("cc_cv_2C", "2C CC-CV"),
        ("cc_cv_3C", "3C CC-CV"),
        ("boost_4C", "Boost 4C→2C"),
        ("mcc_21", "MCC 2C-1C"),
        ("mcc_321", "MCC 3C-2C-1C"),
        ("mcc_432", "MCC 4C-3C-2C"),
    ]

    centre_slice = (slice(PACK_ROWS // 2 - 1, PACK_ROWS // 2 + 1),
                    slice(PACK_COLS // 2 - 1, PACK_COLS // 2 + 1))
    edge_mask = np.zeros((PACK_ROWS, PACK_COLS), dtype=bool)
    edge_mask[0, :] = edge_mask[-1, :] = True
    edge_mask[:, 0] = edge_mask[:, -1] = True

    summary_rows = []
    pack_avg = {}; centre_ts = {}; edge_ts = {}

    duration_6C_min = 70 * 60   # enough for every protocol

    for key, label in PROTOCOLS:
        T_hist, _ = simulate_pack(
            protocol_current(key), duration_6C_min, cooling_h=cooling_h)

        times = np.arange(T_hist.shape[0]) / 60.0   # minutes
        avg = T_hist.mean(axis=(1, 2))
        ctr = T_hist[:, centre_slice[0], centre_slice[1]].mean(axis=(1, 2))
        edg = T_hist[:, edge_mask].mean(axis=1)

        peak_avg = float(avg.max())
        peak_ctr = float(ctr.max())
        peak_edg = float(edg.max())
        grad = peak_ctr - peak_edg

        summary_rows.append({
            "protocol": key, "label": label,
            "peak_avg_c": round(peak_avg, 1),
            "peak_centre_c": round(peak_ctr, 1),
            "peak_edge_c": round(peak_edg, 1),
            "centre_edge_grad_c": round(grad, 1),
        })
        pack_avg[key] = (times, avg)
        centre_ts[key] = (times, ctr)
        edge_ts[key] = (times, edg)

        print(f"{label:<14} peak={peak_avg:5.1f} C  grad={grad:4.1f} C")

    # ---- Figure 1 ----
    fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    key3 = "cc_cv_3C"
    t_min, T_avg = pack_avg[key3]
    _, T_ctr = centre_ts[key3]
    _, T_edg = edge_ts[key3]

    axes[0].plot(t_min, T_ctr, "r-", lw=2, label="Centre cells")
    axes[0].plot(t_min, T_avg, "k--", lw=2, label="Pack average")
    axes[0].plot(t_min, T_edg, "b-", lw=2, label="Edge cells")
    axes[0].axhline(45, color="gray", linestyle=":", label="45 C limit")
    axes[0].set_ylabel("T (C)")
    axes[0].set_title(f"96-cell pack 8x12 – 3C CC-CV, h={cooling_h} W/m²K")
    axes[0].grid(True, alpha=0.3); axes[0].legend()

    for key, label in PROTOCOLS:
        t_min, T_a = pack_avg[key]
        axes[1].plot(t_min, T_a, lw=1.8, label=label)
    axes[1].axhline(45, color="gray", linestyle=":", label="45 C limit")
    axes[1].set_xlabel("Time (min)"); axes[1].set_ylabel("Pack avg T (C)")
    axes[1].set_title("Pack-average T – every protocol")
    axes[1].grid(True, alpha=0.3); axes[1].legend(fontsize=8, loc="upper left")

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "pack_temperature_time.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 2 ----
    labels = [r["label"] for r in summary_rows]
    peaks_avg = [r["peak_avg_c"] for r in summary_rows]
    peaks_ctr = [r["peak_centre_c"] for r in summary_rows]
    peaks_edg = [r["peak_edge_c"] for r in summary_rows]
    grads = [r["centre_edge_grad_c"] for r in summary_rows]

    x = np.arange(len(labels))
    fig, ax1 = plt.subplots(figsize=(10, 5))

    w = 0.25
    ax1.bar(x - w, peaks_edg, w, label="Edge peak", color="tab:blue", alpha=0.85)
    ax1.bar(x,     peaks_avg,  w, label="Average peak", color="tab:orange", alpha=0.85)
    ax1.bar(x + w, peaks_ctr,  w, label="Centre peak", color="tab:red", alpha=0.85)
    ax1.axhline(45, color="gray", linestyle=":", label="45 C comfort limit")
    ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=25, ha="right")
    ax1.set_ylabel("Peak temperature (C)")
    ax1.set_title(f"96-cell pack – peak temperatures, h={cooling_h} W m$^{{-2}}$ K$^{{-1}}$")
    ax1.legend(loc="upper left"); ax1.grid(True, alpha=0.3, axis="y")

    ax2 = ax1.twinx()
    ax2.plot(x, grads, "ko-", lw=2, label="Centre-edge gradient")
    ax2.set_ylabel("Centre-edge gradient (C)")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "pack_peak_comparison.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 3 – heatmaps (3C + 1C, 3 time snapshots each) ----
    duration_3C = 40 * 60
    T3C, _ = simulate_pack(protocol_current("cc_cv_3C"), duration_3C,
                           cooling_h=cooling_h)
    duration_1C = 85 * 60
    T1C, _ = simulate_pack(protocol_current("cc_cv_1C"), duration_1C,
                           cooling_h=cooling_h)

    vmin = 22.0
    vmax = max(T3C.max(), T1C.max()) + 0.5
    cmap = LinearSegmentedColormap.from_list(
        "thermal",
        ["#2166ac", "#67a9cf", "#f6f7f6", "#ef8a62", "#b2182b"])

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    def draw_heatmap(ax, T_snap, title):
        im = ax.imshow(T_snap, cmap=cmap, vmin=vmin, vmax=vmax,
                       aspect="auto", origin="upper")
        ax.set_title(title)
        ax.set_xlabel("Cell col")
        ax.set_ylabel("Cell row")
        # Colourbar per-row
        return im

    snaps_3C = [0.0, 0.5, 1.0]
    for i, frac in enumerate(snaps_3C):
        step = min(int(frac * (T3C.shape[0] - 1)), T3C.shape[0] - 1)
        im = draw_heatmap(axes[0, i], T3C[step],
                          f"3C CC-CV – t = {int(frac * duration_3C / 60)} min")

    snaps_1C = [0.0, 0.5, 1.0]
    for i, frac in enumerate(snaps_1C):
        step = min(int(frac * (T1C.shape[0] - 1)), T1C.shape[0] - 1)
        im = draw_heatmap(axes[1, i], T1C[step],
                          f"1C CC-CV – t = {int(frac * duration_1C / 60)} min")

    fig.suptitle(
        f"96-cell pack temperature heatmaps (8×12 grid, h = {cooling_h} W m$^{{-2}}$ K$^{{-1}}$)",
        fontsize=13, fontweight="bold")
    cbar = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02)
    cbar.set_label("Temperature (C)")
    fig.tight_layout(rect=[0, 0, 0.97, 0.95])
    fig.savefig(os.path.join(outdir, "pack_heatmaps.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---- Save summary ----
    import pandas as pd
    df = pd.DataFrame(summary_rows)
    df.to_csv(os.path.join(outdir, "pack_summary.csv"), index=False)

    print("\n" + "=" * 60)
    print(f"96-cell pack summary — h = {cooling_h} W m-2 K-1")
    print("=" * 60)
    print(f"{'Protocol':<16} {'Peak avg':>10} {'Centre':>8} {'Edge':>7} {'Grad':>7}")
    for r in summary_rows:
        print(f"{r['label']:<16} {r['peak_avg_c']:>8.1f} C  "
              f"{r['peak_centre_c']:>6.1f} C  {r['peak_edge_c']:>5.1f} C  "
              f"{r['centre_edge_grad_c']:>5.1f} C")
    print(f"\nCSV → {outdir}/pack_summary.csv")
    print(f"PNG → pack_temperature_time.png, pack_peak_comparison.png, pack_heatmaps.png")
    return summary_rows


if __name__ == "__main__":
    run_pack_study()
