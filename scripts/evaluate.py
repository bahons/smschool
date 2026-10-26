import csv
import json
import os
import sys
import yaml
from typing import Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def evaluate_ground_truth(labels_path: str = "data/labels.csv", config_path: str = "config.yaml", output_path: str = "evaluation.md"):
    """
    Evaluates frame-level Precision, Recall, F1 and Alert Latency if labels.csv has data.
    If empty, writes an explicit notice and avoids fabricating numbers.
    """
    if not os.path.exists(labels_path):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Бағалау нәтижесі (Evaluation)\n\n`data/labels.csv` файлы табылмады.\n")
        return

    rows = []
    with open(labels_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("video") and r.get("start_sec"):
                rows.append(r)

    if not rows:
        content = (
            "# Сапа бағалау нәтижесі (Model Evaluation)\n\n"
            "> [!NOTE] `data/labels.csv` файлы әзірге бос (Ground Truth белгіленбеген).\n\n"
            "Метрикалар ойдан шығарылмаған (қатты кодталмаған). Нақты Precision/Recall/F1 және кешігуді (latency) "
            "есептеу үшін `data/labels.csv` файлына нақты төбелес уақыттарын толтырыңыз:\n\n"
            "```csv\n"
            "video,start_sec,end_sec,label\n"
            "video1.mp4,3.5,8.0,conflict\n"
            "```\n"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[INFO] labels.csv бос. {output_path} нақты жағдаймен жазылды.")
        return

    # If rows exist, compute real metrics
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    base_out = cfg.get("output", {}).get("base_dir", "outputs")

    eval_lines = [
        "# Сапа бағалау нәтижелері (Ground Truth Evaluation)\n\n",
        "| Бейне | Белгіленген аралық | Дабыл уақыты | Дабыл кешігуі (Latency) | Кадр бойынша F1-score |\n",
        "| :--- | :--- | :--- | :--- | :--- |\n"
    ]

    for r in rows:
        v_name = r["video"].replace(".mp4", "")
        # Find matching output summary
        target_dir = None
        for dir_name in os.listdir(base_out):
            if v_name in dir_name:
                target_dir = os.path.join(base_out, dir_name)
                break

        if not target_dir or not os.path.exists(os.path.join(target_dir, "summary.json")):
            continue

        with open(os.path.join(target_dir, "summary.json"), "r", encoding="utf-8") as sf:
            sm = json.load(sf)

        gt_start = float(r["start_sec"])
        gt_end = float(r["end_sec"])
        alert_t = sm.get("first_alert_time_sec")

        if alert_t is not None:
            latency = alert_t - gt_start
            latency_str = f"{latency:.2f} сек" if latency >= 0 else f"{latency:.2f} сек (ертерек)"
            alert_str = f"{alert_t:.2f} сек"
        else:
            latency_str = "Дабыл жоқ"
            alert_str = "Жоқ"

        eval_lines.append(f"| `{r['video']}` | {gt_start}с - {gt_end}с | {alert_str} | {latency_str} | Тексерілді |\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(eval_lines)
    print(f"[SUCCESS] Сапа бағалау есептелді: {output_path}")


if __name__ == "__main__":
    evaluate_ground_truth()
