"""Figures for the fast-charging study (matplotlib, non-interactive)."""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = plt.cm.tab10(np.linspace(0, 1, 10))


def _style():
    plt.rcParams.update({
        "figure.dpi": 130,
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def plot_retention(cycles_df, outdir, fname="ageing_retention.png"):
    _style()
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for i, (label, group) in enumerate(cycles_df.groupby("label", sort=False)):
        first = group["discharge_capacity_ah"].iloc[0]
        ax.plot(group["cycle"], 100 * group["discharge_capacity_ah"] / first,
                color=COLORS[i], label=label, linewidth=1.8)
    ax.axhline(80, color="grey", linestyle="--", linewidth=1)
    ax.text(1, 80.6, "end-of-life (80%)", color="grey", fontsize=8)
    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Capacity retention (%)")
    ax.set_title("Capacity fade under different charging protocols")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, fname))
    plt.close(fig)


def plot_pareto(summary, outdir):
    _style()
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for i, row in summary.iterrows():
        ax.scatter(row["charge_time_to_target_min"], row["retention_end_pct"],
                   s=110, color=COLORS[i], zorder=3)
        offset = (8, 6) if i % 2 == 0 else (8, -12)
        ax.annotate(row["label"], (row["charge_time_to_target_min"],
                                   row["retention_end_pct"]),
                    textcoords="offset points", xytext=offset, fontsize=8)
    ax.set_xlabel("Charge time to 80% SOC (min)")
    ax.set_ylabel("Capacity retention after test (%)")
    ax.set_title("Fast-charging trade-off: speed versus lifetime")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "ageing_pareto.png"))
    plt.close(fig)


def plot_charge_time(summary, outdir):
    _style()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(summary["label"], summary["charge_time_to_target_min"],
            color=COLORS[:len(summary)])
    for y, value in enumerate(summary["charge_time_to_target_min"]):
        ax.text(value + 0.3, y, f"{value:.1f}", va="center", fontsize=8)
    ax.set_xlabel("Time to 80% SOC (min)")
    ax.set_title("Charging speed by protocol (first cycle)")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charge_time.png"))
    plt.close(fig)


def plot_degradation_modes(summary, outdir):
    _style()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(summary))
    ax.bar(x - 0.2, summary["sei_loss_end_ah"], width=0.4, label="SEI growth",
           color="#4C72B0")
    ax.bar(x + 0.2, summary["plating_loss_end_ah"], width=0.4,
           label="Li plating (dead)", color="#C44E52")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["label"], rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Capacity lost (Ah)")
    ax.set_title("Degradation modes after the test")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "ageing_degradation_modes.png"))
    plt.close(fig)


def plot_temperature(cycles_df, outdir):
    _style()
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for i, (label, group) in enumerate(cycles_df.groupby("label", sort=False)):
        ax.plot(group["cycle"], group["t_max_charge_c"], color=COLORS[i],
                label=label, linewidth=1.6, marker="o", markersize=4)
    ax.axhline(45, color="crimson", linestyle="--", linewidth=1)
    ax.text(1, 45.6, "45 °C comfort limit", color="crimson", fontsize=8)
    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Peak cell temperature (°C)")
    ax.set_title("Peak temperature during charging")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "thermal_peak_temperature.png"))
    plt.close(fig)


def plot_peak_temperature_bar(summary, outdir):
    _style()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(summary["label"], summary["t_max_charge_c"],
            color=COLORS[:len(summary)])
    ax.axvline(45, color="crimson", linestyle="--", linewidth=1)
    for y, value in enumerate(summary["t_max_charge_c"]):
        ax.text(value + 0.4, y, f"{value:.1f} °C", va="center", fontsize=8)
    ax.set_xlabel("Peak cell temperature during charge (°C)")
    ax.set_title("Temperature penalty of each protocol")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "thermal_summary.png"))
    plt.close(fig)


def plot_first_charge_profile(profiles, outdir):
    _style()
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for i, (key, (time_min, temp)) in enumerate(profiles.items()):
        ax.plot(time_min, temp, color=COLORS[i], linewidth=1.7,
                label=key)
    ax.set_xlabel("Time from start of charge (min)")
    ax.set_ylabel("Cell temperature (°C)")
    ax.set_title("Temperature evolution during the first charge")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "thermal_first_charge.png"))
    plt.close(fig)
