"""Render the churn-by-segment figure from ``report/data/profile.json``."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPORT_DIR = Path(__file__).resolve().parents[1]
PROFILE = json.loads((REPORT_DIR / "data" / "profile.json").read_text())
OUT = REPORT_DIR / "figures" / "fig_churn_segments.png"

PANELS = [
    ("churn_by_Contract", "Contract type"),
    ("churn_by_tenure_band", "Tenure (months)"),
    ("churn_by_InternetService", "Internet service"),
    ("churn_by_PaymentMethod", "Payment method"),
]


def main() -> None:
    target = PROFILE["target"]
    overall = target["churn_rate"]
    fig, grid = plt.subplots(2, 2, figsize=(8.5, 5.4), sharey=True)
    axes = grid.ravel()
    for ax, (key, title) in zip(axes, PANELS):
        labels = [k.replace(" (automatic)", "\n(auto)").replace("Electronic check", "Electronic\ncheck") for k in target[key]]
        values = list(target[key].values())
        bars = ax.bar(labels, values, color=["#c0392b" if v > overall else "#2f5d8a" for v in values])
        ax.axhline(overall, color="#555", linestyle="--", linewidth=1)
        ax.set_title(title, fontsize=11)
        ax.tick_params(axis="x", labelsize=8.5)
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.01, f"{v:.0%}", ha="center", fontsize=8.5)
    for ax in (axes[0], axes[2]):
        ax.set_ylabel("Churn rate")
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    axes[0].text(1.6, overall + 0.015, f"overall {overall:.1%}", fontsize=8, color="#555")
    axes[0].set_ylim(0, 0.55)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
