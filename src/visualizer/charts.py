import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Optional
import os


def plot_conflict_timeline(
    timeline_records: List[Dict],
    danger_thresh: float,
    warning_thresh: float,
    alert_time: Optional[float],
    save_path: str,
    title: str = "Conflict Index динамикасы"
) -> None:
    """
    Plots Conflict Index over time with threshold lines and alert trigger markers.
    """
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    times = [r["timestamp"] for r in timeline_records]
    indices = [r["conflict_index"] for r in timeline_records]
    raw_indices = [r["raw_index"] for r in timeline_records]

    plt.figure(figsize=(10, 4.8), dpi=150)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Raw signal (subtle)
    plt.plot(times, raw_indices, color="#b0bec5", alpha=0.5, linewidth=1.0, label="Raw Index (Дерексіз сигнал)")
    # Smoothed signal
    plt.plot(times, indices, color="#1e88e5", linewidth=2.4, label="Smoothed Conflict Index (Тегістелген)")

    # Thresholds
    plt.axhline(y=warning_thresh, color="#fbc02d", linestyle="--", linewidth=1.5, label=f"Ескерту шегі ({warning_thresh})")
    plt.axhline(y=danger_thresh, color="#e53935", linestyle="--", linewidth=1.8, label=f"Қауіп шегі ({danger_thresh})")

    # Alert point marker
    if alert_time is not None:
        # Find index near alert_time
        alert_val = danger_thresh
        for r in timeline_records:
            if abs(r["timestamp"] - alert_time) < 0.1:
                alert_val = r["conflict_index"]
                break

        plt.scatter([alert_time], [alert_val], color="#d32f2f", s=140, zorder=5, edgecolors="black", linewidth=1.5)
        plt.annotate(
            f"ДАБЫЛ СӘТІ\n(t = {alert_time:.2f}s)",
            xy=(alert_time, alert_val),
            xytext=(alert_time + 0.3, alert_val + 0.12),
            arrowprops=dict(facecolor="#d32f2f", shrink=0.08, width=1.5, headwidth=6),
            fontweight="bold",
            color="#b71c1c",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffebee", edgecolor="#ef9a9a")
        )

    plt.title(title, fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Уақыт (секунд)", fontsize=11)
    plt.ylabel("Conflict Index", fontsize=11)
    plt.ylim(-0.05, 1.05)
    plt.xlim(0, max(times) if times else 10)
    plt.legend(loc="upper left", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
