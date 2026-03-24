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
from auth import get_current_role
_role = get_current_role()
if _role == "admin":
    st.sidebar.markdown(
        """
        - 📋 **Index** — портфель проектов
        - 📅 **Gantt** — статус и Гант
        - 💰 **Finance** — финансы
        - 👥 **Team** — команды
        - 🔧 **Operations** — внепроектная работа
        - 🏆 **Motivation** — расчёт премий
        """,
        unsafe_allow_html=False,
    )
else:
    st.sidebar.markdown(
        """
        - 📅 **Gantt** — статус и Гант
        - 👥 **Team** — команды
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
    | 👥 Team | Матрица участия команд в проектах |
    | 🔧 Operations | Внепроектная и операционная работа |
    | 🏆 Motivation | Расчёт и распределение проектной премии |
    """,
)

st.info("Данные обновляются автоматически каждые 5 минут из Google Sheets.")
