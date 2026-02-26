"""
Main entry point — Project Portfolio Dashboard.
This file serves as the home / welcome page.
Authentication is enforced here and on every sub-page.
"""
import streamlit as st

st.set_page_config(
    page_title="AFI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth import render_sidebar_user, require_auth

authenticator = require_auth()

# ── Sidebar ─────────────────────────────────────────────────────────────────
render_sidebar_user(authenticator)

st.sidebar.markdown("---")
st.sidebar.markdown("**Навигация**")
st.sidebar.markdown(
    """
    - 📋 **Index** — портфель проектов
    - 📅 **Gantt** — статус и Гант
    - 💰 **Finance** — финансы
    - 👥 **Team** — команды и премии
    - 🔧 **Operations** — внепроектная работа
    """,
    unsafe_allow_html=False,
)

# ── Home content ─────────────────────────────────────────────────────────────
st.title("📊 AFI Project Portfolio Dashboard")
st.markdown(
    """
    Добро пожаловать в дашборд управления проектным портфелем.

    Выберите раздел в боковом меню слева для просмотра данных.

    | Раздел | Описание |
    |--------|----------|
    | 📋 Index | Сводная таблица всех проектов, KPI-карточки |
    | 📅 Gantt | Диаграмма Ганта и ключевые точки |
    | 💰 Finance | Бюджеты, план/факт оплат 2026 |
    | 👥 Team | Матрица команд и расчёт премий |
    | 🔧 Operations | Внепроектная и операционная работа |
    """,
)

st.info("Данные обновляются автоматически каждые 5 минут из Google Sheets.")
