"""
Page 2 — Gantt chart and milestone plan/fact table
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Gantt — Status", page_icon="📅", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import STATUS_COLORS, load_prj_list, load_prj_status, _find_col, parse_date_range

authenticator = require_auth()
render_sidebar_user(authenticator)

st.title("📅 Статус проектов и диаграмма Ганта")

# ── Load data ────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    prj    = load_prj_list()
    status = load_prj_status()

if prj.empty:
    st.error("Нет данных из 01.PRJ_LIST.")
    st.stop()

code_col   = _find_col(prj, ["Код проекта", "Код", "CODE"])
name_col   = _find_col(prj, ["Сокращенное название проекта", "Сокращённое название проекта", "Название"])
status_col = _find_col(prj, ["Текущий статус", "Статус"])
period_col = _find_col(prj, ["Плановый срок", "Срок"])

# ── Filters ──────────────────────────────────────────────────────────────────
all_projects = ["Все проекты"] + prj[code_col].dropna().tolist() if code_col else ["Все проекты"]
selected = st.selectbox("Выбрать проект", all_projects)

# ── Build Gantt dataframe ────────────────────────────────────────────────────
gantt_rows = []

for _, row in prj.iterrows():
    code    = row.get(code_col, "")   if code_col   else ""
    name    = row.get(name_col, "")   if name_col   else ""
    stat    = row.get(status_col, "") if status_col else ""
    period  = row.get(period_col, "") if period_col else ""

    start, end = parse_date_range(str(period))
    if start is None:
        start = pd.Timestamp("2025-01-01")
    if end is None:
        end = pd.Timestamp("2026-12-31")

    if selected != "Все проекты" and code != selected:
        continue

    gantt_rows.append({
        "Код":    code,
        "Проект": f"{code} — {name}" if name else code,
        "Статус": stat,
        "Начало": start,
        "Конец":  end,
    })

# ── Gantt chart ───────────────────────────────────────────────────────────────
st.subheader("Диаграмма Ганта")

if gantt_rows:
    gantt_df = pd.DataFrame(gantt_rows)
    # Ensure dates are valid
    gantt_df = gantt_df.dropna(subset=["Начало", "Конец"])
    gantt_df = gantt_df[gantt_df["Начало"] < gantt_df["Конец"]]

    if not gantt_df.empty:
        fig = px.timeline(
            gantt_df,
            x_start="Начало",
            x_end="Конец",
            y="Проект",
            color="Статус",
            color_discrete_map=STATUS_COLORS,
            hover_data={"Код": True, "Статус": True},
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            height=max(300, len(gantt_df) * 40 + 100),
            xaxis_title="",
            yaxis_title="",
            legend_title="Статус",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных о сроках для построения Ганта. Проверьте колонку 'Плановый срок'.")
else:
    st.info("Нет проектов для отображения.")

st.divider()

# ── Milestone table from PRJ_STATUS ──────────────────────────────────────────
st.subheader("Ключевые точки (план / факт)")

if status.empty:
    st.info("Данные из 03.PRJ_STATUS недоступны.")
else:
    # Filter by selected project
    disp_status = status.copy()
    if selected != "Все проекты" and "Код проекта" in disp_status.columns:
        disp_status = disp_status[disp_status["Код проекта"] == selected]

    if disp_status.empty:
        st.info(f"Нет данных по проекту {selected}.")
    else:
        # Separate Plan and Fact rows
        if "Тип" in disp_status.columns:
            plan_df = disp_status[disp_status["Тип"].str.strip().str.lower().isin(["план", "plan"])]
            fact_df = disp_status[disp_status["Тип"].str.strip().str.lower().isin(["факт", "fact"])]
        else:
            plan_df = disp_status
            fact_df = pd.DataFrame()

        # Month columns (everything after the fixed ones)
        fixed = {"Код проекта", "Название", "col2", "col3", "Тип", "Ключевая точка", "Срок"}
        month_cols = [c for c in disp_status.columns if c not in fixed]

        if not plan_df.empty and month_cols:
            # Pivot: rows = key points, cols = months
            pivot_data = []
            for _, prow in plan_df.iterrows():
                kp = prow.get("Ключевая точка", "")
                if not kp:
                    continue
                row_data = {"Ключевая точка": kp, "Тип": "План"}
                for mc in month_cols:
                    row_data[mc] = "✅" if str(prow.get(mc, "")).strip() == "1" else ""
                pivot_data.append(row_data)

            if not fact_df.empty:
                for _, frow in fact_df.iterrows():
                    kp = frow.get("Ключевая точка", "")
                    if not kp:
                        continue
                    row_data = {"Ключевая точка": kp, "Тип": "Факт"}
                    for mc in month_cols:
                        row_data[mc] = "✅" if str(frow.get(mc, "")).strip() == "1" else ""
                    pivot_data.append(row_data)

            if pivot_data:
                pivot_df = pd.DataFrame(pivot_data)
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)
            else:
                st.info("Нет данных ключевых точек.")
        else:
            st.dataframe(disp_status, use_container_width=True, hide_index=True)
