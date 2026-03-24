"""
Diagnostic page — inspect raw Google Sheet rows with column indices.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Debug", page_icon="🔍", layout="wide")

from auth import render_sidebar_user, require_auth, require_role
from data.loader import _load_raw, load_prj_status, load_prj_team, load_prj_money, _find_col

authenticator = require_auth()
render_sidebar_user(authenticator)
require_role(["admin"])

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

# ── Parsed team view (for 04.PRJ_TEAM) ────────────────────────────────────────
if sheet == "04.PRJ_TEAM":
    st.divider()
    st.subheader("Распарсенные данные (load_prj_team)")
    with st.spinner("Парсинг..."):
        parsed_team = load_prj_team()
    if parsed_team.empty:
        st.warning("load_prj_team() вернул пустой DataFrame.")
    else:
        code_col = _find_col(parsed_team, ["Код проекта", "Код"])
        name_col = _find_col(parsed_team, ["Название"])
        emp_cols = [c for c in parsed_team.columns if c not in {code_col, name_col} and c]

        st.caption(f"Строк: {len(parsed_team)} | Сотрудников: {len(emp_cols)}")
        st.caption(f"Колонки сотрудников: {emp_cols}")

        # Show full parsed dataframe
        st.dataframe(parsed_team, use_container_width=True)

        # Per-project summary: who is in each project and with what role
        st.subheader("Сводка: роли по проектам")
        VALID_ROLES = {"A", "S", "БА"}
        rows_summary = []
        for _, row in parsed_team.iterrows():
            code_v = str(row.get(code_col, "")).strip() if code_col else ""
            name_v = str(row.get(name_col, "")).strip() if name_col else ""
            for emp in emp_cols:
                role = str(row.get(emp, "")).strip()
                if role in VALID_ROLES:
                    rows_summary.append({
                        "Код": code_v,
                        "Проект": name_v,
                        "Сотрудник": emp,
                        "Роль": role,
                    })
        if rows_summary:
            summary_df = pd.DataFrame(rows_summary)
            st.dataframe(summary_df, use_container_width=True)
            st.caption(f"Итого назначений: {len(summary_df)}")
        else:
            st.warning("Нет ни одного назначения с ролью A/S/БА — проверьте значения в ячейках.")

    st.divider()

# ── Finance monthly columns diagnostic (for 05.PRJ_MONEY_2026) ───────────────
if sheet == "05.PRJ_MONEY_2026":
    st.divider()
    st.subheader("Диагностика: помесячные данные (load_prj_money)")
    with st.spinner("Парсинг..."):
        money_df = load_prj_money()
    if money_df.empty:
        st.warning("load_prj_money() вернул пустой DataFrame.")
    else:
        MONTH_NAMES = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                       "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        plan_cols = [f"{m}_план" for m in MONTH_NAMES]
        fact_cols = [f"{m}_факт" for m in MONTH_NAMES]

        st.caption(f"Строк в money_df: {len(money_df)}  |  is_итого строк: {money_df['is_итого'].sum()}")

        # Show totals per month to detect if data is populated
        non_total = money_df[~money_df["is_итого"]]
        plan_sums = {c: non_total[c].sum() for c in plan_cols if c in non_total.columns}
        fact_sums = {c: non_total[c].sum() for c in fact_cols if c in non_total.columns}

        st.markdown("**Суммы по помесячным колонкам (не-Итого строки):**")
        check_df = pd.DataFrame({
            "Месяц":    MONTH_NAMES,
            "plan_sum": [plan_sums.get(c, 0) for c in plan_cols],
            "fact_sum": [fact_sums.get(c, 0) for c in fact_cols],
        })
        st.dataframe(check_df, use_container_width=True, hide_index=True)

        total_plan_sum = sum(plan_sums.values())
        total_fact_sum = sum(fact_sums.values())
        if total_plan_sum == 0 and total_fact_sum == 0:
            st.error("⚠️ Все помесячные колонки = 0. Возможно, неверные индексы столбцов в листе.")
            st.info("Проверьте реальные индексы в секции ниже: выберите строку «Итого» проекта и смотрите, "
                    "в каких столбцах есть числа.")
        else:
            st.success(f"✅ Данные есть: план={total_plan_sum:,.0f}, факт={total_fact_sum:,.0f}")

        # Show raw first итого row to inspect column positions
        st.markdown("**Первая строка «Итого» из raw-данных (индексы 0-based):**")
        raw_money = _load_raw("05.PRJ_MONEY_2026")
        import re
        _CODE_RE = re.compile(r"^[A-Z]{2,6}\.\d{4}$")
        current = ""
        found_row = None
        for r in raw_money:
            if not r:
                continue
            c0 = r[0].strip() if r else ""
            if c0 and _CODE_RE.match(c0):
                current = c0
            c1 = r[1].strip() if len(r) > 1 else ""
            if current and "итого" in c1.lower():
                found_row = r
                break
        if found_row:
            raw_view = {str(i): v for i, v in enumerate(found_row) if v.strip()}
            st.json(raw_view)
        else:
            st.info("Строка «Итого» не найдена в raw-данных.")
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
