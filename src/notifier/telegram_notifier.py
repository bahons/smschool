import os
import requests
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from typing import Optional


class TelegramNotifier:
    """
    Handles Telegram Alert Mockup generation (clean presentation card image)
    and optional real Telegram dispatch when --send-telegram is specified.
    """

    def __init__(self, bot_token: str = "", chat_id: str = "", location: str = "№204 Кабинет"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.location = location

    def create_mockup_card(
        self,
        screenshot_path: str,
        event_type: str = "ҚАУІП: ТӨБЕЛЕС",
        time_str: str = "00:04.2",
        output_path: str = "outputs/telegram_alert_mockup.png"
    ) -> str:
        """
        Creates a high quality mockup of a Telegram push message card with the screenshot.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        W, H = 800, 680
        canvas = Image.new("RGB", (W, H), (24, 30, 37))  # Telegram Dark Theme background
        draw = ImageDraw.Draw(canvas)

        font_large = self._load_font(24)
        font_med = self._load_font(18)
        font_small = self._load_font(14)

        # Card container
        card_box = (40, 30, W - 40, H - 30)
        draw.rounded_rectangle(card_box, radius=16, fill=(33, 44, 56), outline=(58, 77, 98), width=2)

        # Telegram Header
        draw.text((65, 50), "🤖 Smart School AI Қауіпсіздік Боты", font=font_large, fill=(100, 181, 246))
        draw.text((65, 85), f"🚨 ШҰҒЫЛ ДАБЫЛ: {event_type}", font=font_med, fill=(239, 83, 80))

        # Metadata text
        meta_lines = [
            f"📍 Орны: {self.location}",
            f"⏱ Тіркелген уақыты: {time_str} (Бейнежазбада)",
            f"⚠️ Дереккөз: Камера #04 (YOLOv8-pose Conflict Detector)",
            f"🔔 Әрекет: Мектеп кезекшісіне және әкімшілікке жедел хабарланды."
        ]
        y_text = 120
        for line in meta_lines:
            draw.text((65, y_text), line, font=font_small, fill=(220, 225, 230))
            y_text += 26

        # Insert screenshot thumbnail
        if os.path.exists(screenshot_path):
            try:
                screen = Image.open(screenshot_path)
                screen.thumbnail((W - 130, 360))
                # Paste centered
                px = (W - screen.width) // 2
                canvas.paste(screen, (px, y_text + 15))
                draw.rounded_rectangle((px - 2, y_text + 13, px + screen.width + 2, y_text + 15 + screen.height + 2),
                                       radius=6, outline=(239, 83, 80), width=2)
            except Exception as e:
                print(f"[WARN] Скриншотты картаға қою қатесі: {e}")

        canvas.save(output_path)
        print(f"[INFO] Telegram демо-макеті сақталды: {output_path}")
        return output_path

    def send_real_telegram(
        self,
        screenshot_path: str,
        event_type: str = "ҚАУІП: ТӨБЕЛЕС",
        time_str: str = ""
    ) -> bool:
        """Sends real photo and text to Telegram if credentials are set."""
        if not self.bot_token or not self.chat_id:
            print("[WARN] Telegram bot_token немесе chat_id толтырылмаған! Хабарлама жіберілмеді.")
            return False

        caption = (
            f"🚨 <b>SMART SCHOOL ДАБЫЛ</b> 🚨\n"
            f"<b>Оқиға:</b> {event_type}\n"
            f"<b>Орны:</b> {self.location}\n"
            f"<b>Уақыты:</b> {time_str}\n"
            f"<i>Жүйе адамдар қозғалысы мен білектер кинетикасын талдау арқылы анықтады.</i>"
        )
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        try:
            with open(screenshot_path, "rb") as photo:
                resp = requests.post(
                    url,
                    data={"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"},
                    files={"photo": photo},
                    timeout=10
                )
            if resp.status_code == 200:
                print("[SUCCESS] Telegram-ға нақты хабарлама жіберілді!")
                return True
            else:
                print(f"[ERROR] Telegram жіберу қатесі: {resp.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Telegram қосылу қатесі: {e}")
            return False

    def _load_font(self, size: int):
        candidates = ["C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\tahoma.ttf", "arial.ttf"]
        for c in candidates:
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
        return ImageFont.load_default()
