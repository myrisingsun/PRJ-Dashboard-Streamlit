"""
Page 4 — Project teams and bonus distribution calculator
"""
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Team", page_icon="👥", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import load_prj_team, _find_col

authenticator = require_auth()
render_sidebar_user(authenticator)

st.title("👥 Команды и распределение премий")

# ── Load ─────────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    team = load_prj_team()

if team.empty:
    st.error("Не удалось загрузить данные из листа 04.PRJ_TEAM.")
    st.stop()

code_col = _find_col(team, ["Код проекта", "Код"])
name_col = _find_col(team, ["Название"])
emp_cols = [c for c in team.columns if c not in {code_col, name_col} and c]

# ── Participation matrix ─────────────────────────────────────────────────────
st.subheader("Матрица участия")

ROLE_COLORS = {"A": "#E74C3C", "БА": "#3498DB", "S": "#2ECC71"}

def color_role(val):
    color = ROLE_COLORS.get(str(val).strip(), "")
    return f"background-color: {color}; color: white;" if color else ""

matrix = team.set_index(code_col).reset_index() if code_col else team.copy()

# Normalize: all cells must be plain strings for Arrow serialisation
matrix_clean = matrix[emp_cols].fillna("").astype(str)
matrix_clean = matrix_clean.map(lambda x: "" if x.strip().lower() == "nan" else x.strip())

# Restore project codes as first column for context
if code_col and code_col in matrix.columns:
    matrix_clean.insert(0, code_col, matrix[code_col].values)

try:
    styled = matrix_clean.style.map(color_role, subset=emp_cols)
    st.dataframe(styled, use_container_width=True, hide_index=True)
except Exception:
    st.dataframe(matrix_clean, use_container_width=True, hide_index=True)

st.caption("**A** — руководитель проекта (красный)  |  **БА** — бизнес-аналитик (синий)  |  **S** — участник (зелёный)")

st.divider()

# ── Employee profile ─────────────────────────────────────────────────────────
st.subheader("Сводка по сотруднику")

selected_emp = st.selectbox("Выбрать сотрудника", emp_cols)

if selected_emp:
    emp_data = team[team[selected_emp].fillna("").astype(str).str.strip().isin(["A", "S", "БА"])].copy()

    if emp_data.empty:
        st.info(f"{selected_emp} не участвует ни в одном проекте.")
    else:
        display_cols = [c for c in [code_col, name_col, selected_emp] if c]
        emp_display = emp_data[display_cols].rename(columns={selected_emp: "Роль"})
        st.dataframe(emp_display, use_container_width=True, hide_index=True)
        st.metric("Количество проектов", len(emp_data))

st.divider()

# ── Bonus calculator ─────────────────────────────────────────────────────────
st.subheader("Распределение премии")

bonus_pool = st.number_input(
    "Общий фонд премии (₽)",
    min_value=0,
    value=1_000_000,
    step=10_000,
    format="%d",
)

method = st.radio(
    "Метод распределения",
    options=["Поровну по участникам", "С весом по роли (A=3x, БА=2x, S=1x)", "С весом по количеству проектов"],
)

ROLE_WEIGHTS = {"A": 3, "БА": 2, "S": 1}

if st.button("Рассчитать"):
    # Build participation table: employee → list of roles
    rows = []
    for emp in emp_cols:
        col_data = team[emp].fillna("").astype(str).str.strip()
        roles = col_data[col_data.isin(["A", "S", "БА"])].tolist()
        if roles:
            rows.append({
                "Сотрудник": emp,
                "Количество проектов": len(roles),
                "Роли": ", ".join(roles),
                "Макс. роль": "A" if "A" in roles else ("БА" if "БА" in roles else "S"),
            })

    if not rows:
        st.warning("Нет данных об участии сотрудников.")
    else:
        result_df = pd.DataFrame(rows)

        if method == "Поровну по участникам":
            per_person = bonus_pool / len(result_df)
            result_df["Премия (₽)"] = per_person

        elif "роли" in method:
            result_df["Вес"] = result_df["Макс. роль"].map(ROLE_WEIGHTS).fillna(1)
            total_weight = result_df["Вес"].sum()
            result_df["Премия (₽)"] = result_df["Вес"] / total_weight * bonus_pool

        else:  # by project count
            total_proj = result_df["Количество проектов"].sum()
            result_df["Премия (₽)"] = result_df["Количество проектов"] / total_proj * bonus_pool

        result_df["Премия (₽)"] = result_df["Премия (₽)"].round(2)

        show_cols = ["Сотрудник", "Количество проектов", "Роли", "Премия (₽)"]
        st.dataframe(result_df[show_cols], use_container_width=True, hide_index=True)

        # Total check
        st.metric("Итого распределено", f"{result_df['Премия (₽)'].sum():,.2f} ₽")

        # Download
        csv = result_df[show_cols].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="Скачать CSV",
            data=csv,
            file_name="bonus_distribution.csv",
            mime="text/csv",
        )

        # Viz
        fig = px.bar(
            result_df.sort_values("Премия (₽)", ascending=True),
            x="Премия (₽)",
            y="Сотрудник",
            orientation="h",
            color="Макс. роль",
            color_discrete_map={"A": "#E74C3C", "БА": "#3498DB", "S": "#2ECC71"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=max(300, len(result_df) * 35 + 80))
        st.plotly_chart(fig, use_container_width=True)
