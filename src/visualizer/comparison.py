import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import os
from typing import Dict, Any


def create_comparison_image(
    video1_summary: Dict,
    video2_summary: Dict,
    timeline1: list,
    timeline2: list,
    output_path: str = "outputs/comparison.png"
):
    """
    Creates a clean, publication/presentation-ready comparison infographic image.
    Side-by-side: Video2 (Calm Classroom) vs Video1 (Conflict Alert)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8), dpi=150, gridspec_kw={'height_ratios': [1.2, 1]})
    plt.subplots_adjust(hspace=0.28, wspace=0.18)

    # 1. Top-Left: Calm video screenshot or placeholder
    ax_tl = axes[0, 0]
    ax_tl.set_title("1-ЖАҒДАЙ: Тыныш сынып (video2.mp4)\nКүйі: НОРМА | Дабыл: ЖОҚ", fontsize=12, fontweight="bold", color="#2e7d32")
    calm_img_path = "outputs/video2_calm/alert_screenshot.png"
    # If no alert screenshot, extract middle frame from video
    cap2 = cv2.VideoCapture("data/videos/video2.mp4")
    total2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
    cap2.set(cv2.CAP_PROP_POS_FRAMES, max(1, total2 // 2))
    ret2, f2 = cap2.read()
    cap2.release()
    if ret2 and f2 is not None:
        f2_rgb = cv2.cvtColor(f2, cv2.COLOR_BGR2RGB)
        ax_tl.imshow(f2_rgb)
    ax_tl.axis("off")

    # 2. Top-Right: Fight video alert screenshot
    ax_tr = axes[0, 1]
    ax_tr.set_title("2-ЖАҒДАЙ: Оқушылар төбелесі (video1.mp4)\nКүйі: ҚАУІП: ТӨБЕЛЕС | Дабыл: ІСКЕ ҚОСЫЛДЫ", fontsize=12, fontweight="bold", color="#c62828")
    fight_alert_path = "outputs/video1_fight/alert_screenshot.png"
    if os.path.exists(fight_alert_path):
        f1_img = cv2.imread(fight_alert_path)
        f1_rgb = cv2.cvtColor(f1_img, cv2.COLOR_BGR2RGB)
        ax_tr.imshow(f1_rgb)
    else:
        cap1 = cv2.VideoCapture("data/videos/video1.mp4")
        total1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
        cap1.set(cv2.CAP_PROP_POS_FRAMES, max(1, total1 // 2))
        ret1, f1 = cap1.read()
        cap1.release()
        if ret1 and f1 is not None:
            f1_rgb = cv2.cvtColor(f1, cv2.COLOR_BGR2RGB)
            ax_tr.imshow(f1_rgb)
    ax_tr.axis("off")

    # 3. Bottom-Left: Calm timeline
    ax_bl = axes[1, 0]
    t2 = [r["timestamp"] for r in timeline2]
    idx2 = [r["conflict_index"] for r in timeline2]
    ax_bl.plot(t2, idx2, color="#2e7d32", linewidth=2.2, label="Conflict Index")
    ax_bl.axhline(0.40, color="#fbc02d", linestyle="--", alpha=0.8, label="Ескерту (0.40)")
    ax_bl.axhline(0.65, color="#e53935", linestyle="--", alpha=0.8, label="Қауіп (0.65)")
    ax_bl.set_ylim(-0.05, 1.05)
    ax_bl.set_title("Тыныш сынып: Индекс қауіп шегіне жетпейді", fontsize=11, fontweight="bold")
    ax_bl.set_xlabel("Уақыт (секунд)")
    ax_bl.set_ylabel("Conflict Index")
    ax_bl.legend(loc="upper right", fontsize=9)
    ax_bl.grid(True, linestyle=":", alpha=0.6)

    # 4. Bottom-Right: Fight timeline
    ax_br = axes[1, 1]
    t1 = [r["timestamp"] for r in timeline1]
    idx1 = [r["conflict_index"] for r in timeline1]
    ax_br.plot(t1, idx1, color="#c62828", linewidth=2.2, label="Conflict Index")
    ax_br.axhline(0.40, color="#fbc02d", linestyle="--", alpha=0.8, label="Ескерту (0.40)")
    ax_br.axhline(0.65, color="#e53935", linestyle="--", alpha=0.8, label="Қауіп (0.65)")
    if video1_summary.get("first_alert_time_sec") is not None:
        at = video1_summary["first_alert_time_sec"]
        ax_br.scatter([at], [0.65], color="#b71c1c", s=120, zorder=5)
        ax_br.annotate(f"ДАБЫЛ ({at:.1f}s)", (at, 0.65), textcoords="offset points",
                       xytext=(10, 10), fontweight="bold", color="#b71c1c",
                       arrowprops=dict(arrowstyle="->", color="#b71c1c", lw=1.5))
    ax_br.set_ylim(-0.05, 1.05)
    ax_br.set_title("Төбелес: 2 сек үздіксіз шектен асу → ДАБЫЛ", fontsize=11, fontweight="bold")
    ax_br.set_xlabel("Уақыт (секунд)")
    ax_br.set_ylabel("Conflict Index")
    ax_br.legend(loc="upper left", fontsize=9)
    ax_br.grid(True, linestyle=":", alpha=0.6)

    plt.suptitle("Smart School AI: Салыстырмалы Анализ (Тыныш жағдай vs Конфликт)", fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"[INFO] Салыстыру суреті сақталды: {output_path}")
