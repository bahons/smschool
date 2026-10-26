import argparse
import os
import sys
import yaml
import cv2
from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from src.pipeline import process_video
from src.visualizer.comparison import create_comparison_image
from src.notifier.telegram_notifier import TelegramNotifier
from scripts.evaluate import evaluate_ground_truth
from scripts.create_presentation import build_presentation


def make_alert_gif(video_path: str, alert_time: float, output_gif: str, duration_sec: float = 6.0):
    """Generates a 5-8 second lightweight GIF around the alert event."""
    os.makedirs(os.path.dirname(output_gif), exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    start_sec = max(0.0, alert_time - 1.0)
    end_sec = start_sec + duration_sec

    start_f = int(start_sec * fps)
    end_f = int(end_sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
    frames = []

    curr = start_f
    while curr <= end_f:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        if curr % 2 == 0:
            small = cv2.resize(frame, (540, 304))
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb))
        curr += 1

    cap.release()

    if frames:
        frames[0].save(
            output_gif,
            save_all=True,
            append_images=frames[1:],
            duration=66,
            loop=0,
            optimize=True
        )
        print(f"[INFO] Презентациялық GIF сақталды: {output_gif}")


def main():
    parser = argparse.ArgumentParser(description="Smart School AI - Демо және Тестілеу жүйесі")
    parser.add_argument("--blur-head", action="store_true", help="Бас аймағын бұлдырлау (жеке құпиялылық)")
    parser.add_argument("--send-telegram", action="store_true", help="Нақты Telegram-ға жіберу")
    parser.add_argument("--config", default="config.yaml", help="Конфигурация файлы")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("=" * 65)
    print("      SMART SCHOOL: AI ДЕМО ЖӘНЕ ТЕСТІЛЕУ ПЛАТФОРМАСЫ      ")
    print("=" * 65)
    if args.blur_head:
        print("[РЕЖИМ] Жеке құпиялылық қосулы (--blur-head)")
    if args.send_telegram:
        print("[РЕЖИМ] Нақты Telegram хабарламасы қосулы (--send-telegram)")

    # 1. Тыныш видеоны өңдеу (video2)
    calm_cfg = cfg["videos"]["normal"]
    res_calm = process_video(calm_cfg, cfg, blur_head=args.blur_head)

    # 2. Төбелес видеоны өңдеу (video1)
    fight_cfg = cfg["videos"]["conflict"]
    res_fight = process_video(fight_cfg, cfg, blur_head=args.blur_head)

    # 3. Салыстырмалы инфографика жасау
    print("\n[STEP] Салыстырмалы инфографика қалыптастырылуда...")
    comparison_img_path = os.path.join(cfg.get("output", {}).get("base_dir", "outputs"), "comparison.png")
    create_comparison_image(
        video1_summary=res_fight["summary"],
        video2_summary=res_calm["summary"],
        timeline1=res_fight["timeline"],
        timeline2=res_calm["timeline"],
        output_path=comparison_img_path
    )

    # 4. Telegram демо макеті және хабарлау
    print("\n[STEP] Telegram демо-макеті дайындалуда...")
    tg_cfg = cfg.get("telegram", {})
    notifier = TelegramNotifier(
        bot_token=tg_cfg.get("bot_token", ""),
        chat_id=tg_cfg.get("chat_id", ""),
        location=tg_cfg.get("location", "№204 Кабинет (2-қабат)")
    )
    alert_screenshot = os.path.join(res_fight["video_out_dir"], "alert_screenshot.png")
    alert_time = res_fight["summary"].get("first_alert_time_sec") or 4.0
    tg_mock_path = os.path.join(cfg.get("output", {}).get("base_dir", "outputs"), "telegram_alert_mockup.png")

    notifier.create_mockup_card(
        screenshot_path=alert_screenshot,
        event_type="ҚАУІП: ТӨБЕЛЕС",
        time_str=f"{alert_time:.1f} сек",
        output_path=tg_mock_path
    )

    if args.send_telegram:
        notifier.send_real_telegram(
            screenshot_path=alert_screenshot,
            event_type="ҚАУІП: ТӨБЕЛЕС",
            time_str=f"{alert_time:.1f} сек"
        )

    # 5. Презентация материалдары (GIF, Assets, PPTX)
    print("\n[STEP] Презентациялық материалдар жинақталуда...")
    assets_dir = os.path.join(cfg.get("output", {}).get("base_dir", "outputs"), "presentation_assets")
    os.makedirs(assets_dir, exist_ok=True)

    # 5-8 сек GIF анимациясы
    gif_path = os.path.join(assets_dir, "conflict_alert_moment.gif")
    annotated_fight_video = os.path.join(res_fight["video_out_dir"], "annotated.mp4")
    make_alert_gif(annotated_fight_video, alert_time, gif_path, duration_sec=6.0)

    # 6 слайдтық презентация
    pptx_path = os.path.join(assets_dir, "SmartSchool_Presentation.pptx")
    build_presentation(pptx_path)

    # 6. Сапа бағалау (Evaluation)
    print("\n[STEP] Сапа бағалау тексерілуде...")
    evaluate_ground_truth(labels_path="data/labels.csv", config_path=args.config, output_path="evaluation.md")

    print("\n" + "=" * 65)
    print(" БАРЛЫҚ ДЕМО ЖӘНЕ ТЕСТІЛЕУ НӘТИЖЕЛЕРІ СӘТТІ АЯҚТАЛДЫ! ")
    print("=" * 65)
    print(f" 1. Тыныш видео нәтижесі: outputs/{calm_cfg['name']}/")
    print(f" 2. Төбелес видео нәтижесі: outputs/{fight_cfg['name']}/")
    print(f" 3. Салыстыру инфографикасы: outputs/comparison.png")
    print(f" 4. Telegram макеті: outputs/telegram_alert_mockup.png")
    print(f" 5. Презентация слайдтары: outputs/presentation_assets/SmartSchool_Presentation.pptx")
    print(f" 6. Төбелес GIF анимациясы: outputs/presentation_assets/conflict_alert_moment.gif")
    print(f" 7. Сапа бағалау есебі: evaluation.md")
    print("=" * 65)


if __name__ == "__main__":
    main()
