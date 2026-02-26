"""
Diagnostic page — inspect raw Google Sheet rows with column indices.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Debug", page_icon="🔍", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import _load_raw, load_prj_status

authenticator = require_auth()
render_sidebar_user(authenticator)

st.title("🔍 Диагностика сырых данных")

sheet = st.selectbox("Лист", [
    "01.PRJ_LIST",
    "02.OPER_LIST",
    "03.PRJ_STATUS",
    "04.PRJ_TEAM",
    "05.PRJ_MONEY_2026",
])

# ── Parsed status view (for 03.PRJ_STATUS) ────────────────────────────────────
if sheet == "03.PRJ_STATUS":
    st.divider()
    st.subheader("Распарсенные данные (load_prj_status)")
    with st.spinner("Парсинг..."):
        parsed = load_prj_status()
    if parsed.empty:
        st.warning("load_prj_status() вернул пустой DataFrame.")
    else:
        # Show only fixed columns to keep it readable
        fixed_view_cols = [c for c in ["№", "Код проекта", "Название работы", "col3", "Тип", "Доп. описание", "Срок"] if c in parsed.columns]
        prj_codes = sorted(parsed["Код проекта"].dropna().unique().tolist()) if "Код проекта" in parsed.columns else []
        sel_prj = st.selectbox("Фильтр по проекту (для проверки наименований работ)", ["— все —"] + prj_codes)
        view_df = parsed[fixed_view_cols].copy()
        if sel_prj != "— все —":
            view_df = view_df[parsed["Код проекта"] == sel_prj]
        st.dataframe(view_df.reset_index(drop=True), use_container_width=True)
        st.caption(
            "col3 (D) — столбец с наименованиями работ. "
            "Название работы (C) — может содержать полное название проекта (не работы). "
            "Тип = Plan/Факт/Факт."
        )

        # ── Gantt work_name simulation ─────────────────────────────────────────
        st.subheader("Симуляция: что читает Gantt (work_name для Plan-строк)")
        st.caption(
            "Показывает финальное значение work_name по той же логике, "
            "что применяет страница Gantt: col3 (D) → Название работы (C) → Доп. описание."
        )

        if "Тип" in parsed.columns:
            plan_rows = (
                parsed[parsed["Код проекта"] == sel_prj]
                if sel_prj != "— все —"
                else parsed
            )
            plan_rows = plan_rows[
                plan_rows["Тип"].str.strip().str.lower().isin(["план", "plan"])
            ]

            sim_rows = []
            for _, pr in plan_rows.iterrows():
                c3   = str(pr.get("col3",           "")).strip()
                nazv = str(pr.get("Название работы","")).strip()
                dop  = str(pr.get("Доп. описание",  "")).strip()
                wn   = c3 or nazv or dop or "—"
                sim_rows.append({
                    "Код проекта":     pr.get("Код проекта", ""),
                    "col3 (D)":        c3   or "<пусто>",
                    "Название работы": nazv or "<пусто>",
                    "Доп. описание":   dop  or "<пусто>",
                    "→ work_name":     wn,
                })

            if sim_rows:
                sim_df = pd.DataFrame(sim_rows)
                st.dataframe(sim_df.reset_index(drop=True), use_container_width=True)
            else:
                st.info("Plan-строк не найдено для выбранного фильтра.")
        else:
            st.warning("Столбец 'Тип' отсутствует в parsed DataFrame.")

    st.divider()

with st.spinner("Загрузка..."):
    raw = _load_raw(sheet)

st.success(f"Загружено строк: {len(raw)}")

col_a, col_b = st.columns([2, 1])
with col_a:
    filter_col = st.number_input("Фильтровать по столбцу №", min_value=0, max_value=50, value=0)
    filter_val = st.text_input("Значение для фильтра (пусто = показать все)", value="PRMN.0001")
with col_b:
    row_from = st.number_input("Строки с (#, 1-based)", min_value=1, value=1)
    row_to   = st.number_input("по (#, 1-based)",       min_value=1, value=min(50, len(raw)))

rows_out = []
for i, row in enumerate(raw):
    line_no = i + 1
    if line_no < row_from or line_no > row_to:
        continue
    c_val = row[filter_col].strip() if len(row) > filter_col else ""
    if filter_val and c_val != filter_val:
        continue
    rows_out.append({"#": line_no, **{str(j): v for j, v in enumerate(row)}})

if rows_out:
    df = pd.DataFrame(rows_out).fillna("")
    st.dataframe(df, use_container_width=True)
    st.caption("Заголовки столбцов = индексы (0-based). # = номер строки в листе (1-based).")
else:
    st.info("Строк по заданному фильтру не найдено.")
