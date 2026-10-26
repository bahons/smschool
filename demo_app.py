import streamlit as st
import json
import os
import yaml
import pandas as pd
from PIL import Image

st.set_page_config(
    page_title="Smart School AI - Демо Панелі",
    page_icon="🏫",
    layout="wide"
)

st.title("🏫 Smart School: AI Демо және Тестілеу Панелі")
st.markdown("Бұл веб-интерфейс презентация кезінде қауіпсіздік мониторингін және нақты уақыттағы салыстырмалы нәтижелерді көрсетуге арналған.")

# Load config
if os.path.exists("config.yaml"):
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
else:
    cfg = {}

tab1, tab2, tab3 = st.tabs(["📊 Салыстырмалы Анализ", "🎬 Видео нәтижелері", "📑 Есептер және Telegram"])

with tab1:
    st.header("Тыныш сынып vs Оқушылар төбелесі")
    comp_path = "outputs/comparison.png"
    if os.path.exists(comp_path):
        st.image(comp_path, use_container_width=True)
    else:
        st.info("Салыстыру суреті әлі жасалмаған. Алдымен `python run_demo.py` іске қосыңыз.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Тыныш сынып (video2.mp4)")
        sum2_path = "outputs/video2_calm/summary.json"
        if os.path.exists(sum2_path):
            with open(sum2_path, "r", encoding="utf-8") as f:
                s2 = json.load(f)
            st.metric("Күйі", "НОРМА (Жасыл)", delta="Қауіп жоқ")
            st.metric("Дабыл саны", s2.get("total_alerts", 0))
            st.metric("Ең жоғары индекс", f"{s2.get('peak_conflict_index', 0):.2f}")
            st.metric("Орташа өңдеу FPS", f"{s2.get('avg_processing_fps', 0):.1f}")

    with col2:
        st.subheader("Конфликт / Төбелес (video1.mp4)")
        sum1_path = "outputs/video1_fight/summary.json"
        if os.path.exists(sum1_path):
            with open(sum1_path, "r", encoding="utf-8") as f:
                s1 = json.load(f)
            st.metric("Күйі", "ҚАУІП: ТӨБЕЛЕС (Қызыл)", delta="Дабыл соғылды", delta_color="inverse")
            st.metric("Дабыл тіркелген уақыт", f"{s1.get('first_alert_time_sec', 0):.2f} сек")
            st.metric("Ең жоғары индекс", f"{s1.get('peak_conflict_index', 0):.2f}")
            st.metric("Тест қорытындысы", "ӨТТІ (PASSED)" if s1.get("test_passed") else "ӨТПЕДІ")

with tab2:
    st.header("Өңделген бейнежазбалар (Annotated Videos)")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.subheader("video2.mp4 (Тыныш сынып)")
        v2_path = "outputs/video2_calm/annotated.mp4"
        if os.path.exists(v2_path):
            st.video(v2_path)
            st.image("outputs/video2_calm/conflict_timeline.png", caption="Тыныш сыныптың Conflict Index графигі")

    with col_v2:
        st.subheader("video1.mp4 (Балалар төбелесі)")
        v1_path = "outputs/video1_fight/annotated.mp4"
        if os.path.exists(v1_path):
            st.video(v1_path)
            st.image("outputs/video1_fight/conflict_timeline.png", caption="Төбелес бейнесінің Conflict Index графигі")

with tab3:
    st.header("Жедел хабарлама және Бағалау есебі")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Telegram Дабыл Макеті")
        tg_mock = "outputs/telegram_alert_mockup.png"
        if os.path.exists(tg_mock):
            st.image(tg_mock, caption="Мектеп кезекшісі мен әкімшілікке баратын хабарлама")

        gif_mock = "outputs/presentation_assets/conflict_alert_moment.gif"
        if os.path.exists(gif_mock):
            st.subheader("Дабыл сәтінің GIF анимациясы")
            st.image(gif_mock, caption="Төбелес кезіндегі 6 секундтық үзінді")

    with col_t2:
        st.subheader("evaluation.md нәтижелері")
        if os.path.exists("evaluation.md"):
            with open("evaluation.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
