"""
Page 7 — Motivation: project bonus distribution calculator
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Motivation", page_icon="🏆", layout="wide")

from auth import render_sidebar_user, require_auth, require_role
from data.loader import load_prj_team, _find_col

authenticator = require_auth()
render_sidebar_user(authenticator)
require_role(["admin"])

st.title("🏆 Мотивация — расчёт проектной премии")

# ── Load ─────────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    team = load_prj_team()

if team.empty:
    st.error("Не удалось загрузить данные из листа 04.PRJ_TEAM.")
    st.stop()

code_col = _find_col(team, ["Код проекта", "Код"])
name_col = _find_col(team, ["Название"])
emp_cols = [c for c in team.columns if c not in {code_col, name_col} and c]

VALID_ROLES = {"A", "S", "БА"}
ROLE_COLORS = {"A": "#E74C3C", "БА": "#3498DB", "S": "#2ECC71"}
ROLE_WEIGHTS = {"A": 3, "БА": 2, "S": 1}

# ── KPI ───────────────────────────────────────────────────────────────────────
emp_project_counts: dict = {}
for emp in emp_cols:
    col_data = team[emp].fillna("").astype(str).str.strip()
    active = col_data[col_data.isin(VALID_ROLES)]
    if not active.empty:
        emp_project_counts[emp] = len(active)

k1, k2, k3 = st.columns(3)
k1.metric("Сотрудников в командах", len(emp_project_counts))
k2.metric("Проектов", len(team))
k3.metric("Среднее проектов / чел.",
          round(sum(emp_project_counts.values()) / len(emp_project_counts), 1)
          if emp_project_counts else 0.0)

st.divider()

# ── Калькулятор премий ────────────────────────────────────────────────────────
st.subheader("Распределение премии")

col_left, col_right = st.columns([1, 2])

with col_left:
    bonus_pool = st.number_input(
        "Общий фонд премии (₽)",
        min_value=0,
        value=1_000_000,
        step=10_000,
        format="%d",
    )

    method = st.radio(
        "Метод распределения",
        options=[
            "Поровну по участникам",
            "С весом по роли (A=3x, БА=2x, S=1x)",
            "С весом по количеству проектов",
        ],
    )

    calc_btn = st.button("Рассчитать", type="primary")


def fmt_bonus_label(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} млн"
    if v >= 1_000:
        return f"{v / 1_000:.1f} тыс"
    return f"{v:.0f} ₽"


if calc_btn:
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

        else:
            total_proj = result_df["Количество проектов"].sum()
            result_df["Премия (₽)"] = result_df["Количество проектов"] / total_proj * bonus_pool

        result_df["Премия (₽)"] = result_df["Премия (₽)"].round(2)

        show_cols = ["Сотрудник", "Количество проектов", "Роли", "Премия (₽)"]

        with col_right:
            st.dataframe(result_df[show_cols], use_container_width=True, hide_index=True)
            st.metric("Итого распределено", f"{result_df['Премия (₽)'].sum():,.2f} ₽")

            csv = result_df[show_cols].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="Скачать CSV",
                data=csv,
                file_name="bonus_distribution.csv",
                mime="text/csv",
            )

        st.divider()

        sorted_df = result_df.sort_values("Премия (₽)", ascending=True)
        bar_colors = sorted_df["Макс. роль"].map(ROLE_COLORS).fillna("#95A5A6").tolist()

        fig = go.Figure(go.Bar(
            y=sorted_df["Сотрудник"],
            x=sorted_df["Премия (₽)"],
            orientation="h",
            marker_color=bar_colors,
            text=sorted_df["Премия (₽)"].apply(fmt_bonus_label),
            textposition="outside",
            cliponaxis=False,
        ))
        fig.update_layout(
            height=max(300, len(sorted_df) * 35 + 80),
            margin=dict(l=0, r=130, t=10, b=0),
            plot_bgcolor="#ffffff",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_title="₽",
            yaxis_title="",
            showlegend=False,
        )
        fig.update_xaxes(gridcolor="#E8E8E8", showgrid=True)
        st.plotly_chart(fig, use_container_width=True)
