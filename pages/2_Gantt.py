"""
Page 2 — Gantt chart and milestone plan/fact table (Sprint 2 redesign)
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from typing import Optional

st.set_page_config(page_title="Gantt — Status", page_icon="📅", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import (
    STATUS_COLORS, load_prj_list, load_prj_status,
    _find_col, parse_date_range, _parse_month_label,
)

authenticator = require_auth()
render_sidebar_user(authenticator)

st.title("📅 Статус проектов и диаграмма Ганта")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    prj    = load_prj_list()
    status = load_prj_status()

if prj.empty:
    st.error("Нет данных из 01.PRJ_LIST.")
    st.stop()

code_col     = _find_col(prj, ["Код проекта", "Код", "CODE"])
name_col     = _find_col(prj, ["Сокращенное название проекта", "Сокращённое название проекта", "Название"])
status_col   = _find_col(prj, ["Текущий статус", "Статус"])
period_col   = _find_col(prj, ["Плановый срок", "Срок"])
priority_col = _find_col(prj, ["Приоритет", "Priority"])

_PRIORITY_ORDER = {"Высокий": 0, "Средний": 1, "Низкий": 2}

# Sort by priority (ascending: Высокий first) — used for both Gantt and table
if priority_col:
    prj = prj.copy()
    prj["_prio"] = prj[priority_col].map(_PRIORITY_ORDER).fillna(99)
    prj = prj.sort_values("_prio").drop(columns=["_prio"])

# ── Sidebar filters ───────────────────────────────────────────────────────────
all_projects  = prj[code_col].dropna().tolist()           if code_col    else []
all_statuses  = sorted(prj[status_col].dropna().unique()) if status_col  else []
all_priorities = ["Высокий", "Средний", "Низкий"]

with st.sidebar:
    st.divider()
    st.markdown("### Фильтры")

    st.caption("Проекты")
    if st.button("Все проекты", use_container_width=True, key="gantt_btn_all_codes"):
        st.session_state["gantt_sel_codes"] = all_projects
    sel_codes = st.multiselect(
        "Проекты",
        options=all_projects,
        default=st.session_state.get("gantt_sel_codes", all_projects),
        key="gantt_sel_codes",
        label_visibility="collapsed",
    )

    st.caption("Статус")
    if st.button("Все статусы", use_container_width=True, key="gantt_btn_all_statuses"):
        st.session_state["gantt_sel_statuses"] = all_statuses
    sel_statuses = st.multiselect(
        "Статус",
        options=all_statuses,
        default=st.session_state.get("gantt_sel_statuses", all_statuses),
        key="gantt_sel_statuses",
        label_visibility="collapsed",
    )

    st.caption("Приоритет")
    if st.button("Все приоритеты", use_container_width=True, key="gantt_btn_all_priorities"):
        st.session_state["gantt_sel_priorities"] = all_priorities
    sel_priorities = st.multiselect(
        "Приоритет",
        options=all_priorities,
        default=st.session_state.get("gantt_sel_priorities", all_priorities),
        key="gantt_sel_priorities",
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("🔄 Обновить данные", use_container_width=True, key="gantt_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered_prj = prj.copy()
if sel_codes and code_col:
    filtered_prj = filtered_prj[filtered_prj[code_col].isin(sel_codes)]
if sel_statuses and status_col:
    filtered_prj = filtered_prj[filtered_prj[status_col].isin(sel_statuses)]
if sel_priorities and priority_col:
    filtered_prj = filtered_prj[filtered_prj[priority_col].isin(sel_priorities)]

# ── Identify month columns in status df ──────────────────────────────────────
_FIXED_STATUS_COLS = {"№", "Код проекта", "Название работы", "col3", "Тип", "Доп. описание", "Срок"}
month_cols: list[str] = (
    [c for c in status.columns if c not in _FIXED_STATUS_COLS]
    if not status.empty else []
)
month_dates: list[Optional[pd.Timestamp]] = [_parse_month_label(c) for c in month_cols]


# ── Helper: work item date range from a Plan row ──────────────────────────────
def _work_item_date_range(
    plan_row: pd.Series,
) -> tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """Find first/last month col with '1' or 'X' in plan_row."""
    first_idx = last_idx = None
    for i, col in enumerate(month_cols):
        val = str(plan_row.get(col, "")).strip()
        if val in ("1", "X", "x"):
            if first_idx is None:
                first_idx = i
            last_idx = i

    if first_idx is None or month_dates[first_idx] is None:
        return None, None

    start    = month_dates[first_idx]
    end_base = month_dates[last_idx] if (last_idx is not None and month_dates[last_idx] is not None) else start
    try:
        end = end_base + pd.DateOffset(months=1)
    except Exception:
        end = end_base
    return start, end


# ── Build Gantt dataframe ─────────────────────────────────────────────────────
gantt_rows = []

for _, row in filtered_prj.iterrows():
    code   = str(row.get(code_col,   "") or "") if code_col   else ""
    name   = str(row.get(name_col,   "") or "") if name_col   else ""
    stat   = str(row.get(status_col, "") or "") if status_col else ""
    period = str(row.get(period_col, "") or "") if period_col else ""

    start, end = parse_date_range(period)
    if start is None:
        start = pd.Timestamp("2025-01-01")
    if end is None:
        end = pd.Timestamp("2026-12-31")

    label = f"{code} — {name}" if name else code
    gantt_rows.append({
        "Задача":    label,
        "Начало":    start,
        "Конец":     end,
        "Тип_бар":  "Проект",
        "Цвет_ключ": stat,
        "Код":       code,
    })

    # Work items from PRJ_STATUS for this project
    if not status.empty and "Код проекта" in status.columns and month_cols:
        prj_status = status[status["Код проекта"] == code]
        plan_mask  = prj_status["Тип"].str.strip().str.lower().isin(["план", "plan"])
        for _, prow in prj_status[plan_mask].iterrows():
            work_name = str(prow.get("col3", "")).strip()
            if not work_name:
                work_name = str(prow.get("Название работы", "")).strip()
            if not work_name:
                work_name = str(prow.get("Доп. описание", "")).strip()
            if not work_name:
                continue
            w_start, w_end = _work_item_date_range(prow)
            if w_start is None:
                continue
            gantt_rows.append({
                "Задача":    f"  · {work_name}",
                "Начало":    w_start,
                "Конец":     w_end,
                "Тип_бар":  "Работа",
                "Цвет_ключ": "Работа",
                "Код":       code,
            })

# ── Gantt chart ───────────────────────────────────────────────────────────────
st.subheader("Digital Projects Roadmap")

if gantt_rows:
    gantt_df = pd.DataFrame(gantt_rows)
    gantt_df = gantt_df.dropna(subset=["Начало", "Конец"])
    gantt_df = gantt_df[gantt_df["Начало"] < gantt_df["Конец"]]

    if not gantt_df.empty:
        color_map  = {**STATUS_COLORS, "Работа": "#AAAAAA", "": "#BDC3C7"}
        # task_order is High-priority-first; plotly default places first category at
        # the BOTTOM of the y-axis, so we pass the reversed list to categoryarray —
        # the last entry (originally first = High priority) ends up at the TOP.
        task_order = gantt_df["Задача"].tolist()

        fig = px.timeline(
            gantt_df,
            x_start="Начало",
            x_end="Конец",
            y="Задача",
            color="Цвет_ключ",
            color_discrete_map=color_map,
            hover_data={"Код": True, "Тип_бар": True},
        )
        fig.update_yaxes(
            categoryorder="array",
            categoryarray=task_order[::-1],   # reversed → High priority at top
        )
        fig.update_xaxes(
            dtick="M1",
            tickformat="%b %Y",
            ticklabelmode="period",
            showgrid=True,
            gridcolor="#E8E8E8",
            tickangle=-45,
        )
        fig.update_layout(
            height=max(300, len(gantt_df) * 30 + 100),
            xaxis_title="",
            yaxis_title="",
            legend_title="Статус",
            margin=dict(l=0, r=0, t=10, b=50),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных о сроках для построения Ганта. Проверьте колонку 'Плановый срок'.")
else:
    st.info("Нет проектов для отображения.")

st.divider()

# ── HTML status table ─────────────────────────────────────────────────────────
st.subheader("Исполнение ключевых работ")

if status.empty:
    st.info("Данные из 03.PRJ_STATUS недоступны.")
else:
    # Trim month_cols: keep range from first to last col with any value
    first_non_empty_idx: Optional[int] = None
    last_non_empty_idx:  Optional[int] = None
    for i, col in enumerate(month_cols):
        if status[col].replace("", None).notna().any():
            if first_non_empty_idx is None:
                first_non_empty_idx = i
            last_non_empty_idx = i

    if first_non_empty_idx is not None:
        trimmed_months = month_cols[first_non_empty_idx : last_non_empty_idx + 1]
    else:
        trimmed_months = month_cols

    if not trimmed_months:
        st.info("Нет месячных данных в 03.PRJ_STATUS.")
        st.stop()

    # Build year/month header structure (preserve insertion order)
    year_headers: dict[str, int] = {}
    month_labels: list[str] = []
    for col in trimmed_months:
        parts = col.split("_", 1)
        if len(parts) == 2:
            year_str, month_str = parts
            year_headers[year_str] = year_headers.get(year_str, 0) + 1
            month_labels.append(month_str)
        else:
            year_headers.setdefault("", 0)
            year_headers[""] += 1
            month_labels.append(col)

    def cell_symbol(val: str) -> str:
        v = val.strip()
        if v == "1":
            return '<span class="dot">●</span>'
        if v.upper() == "X":
            return '<span class="star">★</span>'
        return ""

    # ── Shared table structure ────────────────────────────────────────────────
    n_month    = len(trimmed_months)

    month_pct = round(75 / n_month, 2) if n_month else 3
    colgroup = (
        '<colgroup>'
        '<col style="width:20%">'
        '<col style="width:5%">'
        + f'<col style="width:{month_pct}%">' * n_month
        + '</colgroup>'
    )

    year_row_html  = "".join(
        f'<th class="year-th" colspan="{colspan}">{year_label}</th>'
        for year_label, colspan in year_headers.items()
    )
    month_row_html = "".join(f"<th>{m}</th>" for m in month_labels)

    thead = (
        f'<thead>'
        f'<tr><th class="year-th" colspan="2"></th>{year_row_html}</tr>'
        f'<tr><th style="text-align:left;">Работа</th><th>Тип</th>{month_row_html}</tr>'
        f'</thead>'
    )

    # ── Build one HTML block with all project tables ───────────────────────────
    prj_order = filtered_prj[code_col].dropna().tolist() if code_col else (
        status["Код проекта"].dropna().unique().tolist()
    )

    blocks: list[str] = []

    for prj_code in prj_order:
        prj_status_rows = status[status["Код проекта"] == prj_code]
        if prj_status_rows.empty:
            continue

        prj_display = prj_code
        if code_col and name_col:
            prj_row_match = prj[prj[code_col] == prj_code]
            if not prj_row_match.empty:
                nm = str(prj_row_match.iloc[0].get(name_col, "")).strip()
                if nm:
                    prj_display = f"{prj_code} — {nm}"

        tbody_parts: list[str] = []
        rows_list = list(prj_status_rows.iterrows())
        i = 0
        while i < len(rows_list):
            _, cur_row = rows_list[i]
            row_type = str(cur_row.get("Тип", "")).strip().lower()

            if row_type not in ("план", "plan"):
                i += 1
                continue

            plan_row = cur_row
            fact_row: Optional[pd.Series] = None
            if i + 1 < len(rows_list):
                _, nxt = rows_list[i + 1]
                if str(nxt.get("Тип", "")).strip().lower() in ("факт", "fact"):
                    fact_row = nxt
                    i += 2
                else:
                    i += 1
            else:
                i += 1

            work_name = str(plan_row.get("col3", "")).strip()
            if not work_name:
                work_name = str(plan_row.get("Название работы", "")).strip()
            if not work_name:
                work_name = str(plan_row.get("Доп. описание", "")).strip()

            plan_cells = "".join(
                f"<td>{cell_symbol(str(plan_row.get(c, '')))}</td>"
                for c in trimmed_months
            )
            tbody_parts.append(
                f'<tr class="plan-row">'
                f'<td class="work-name">{work_name}</td>'
                f'<td class="type-cell">План</td>'
                f'{plan_cells}</tr>'
            )

            if fact_row is not None:
                fact_cells = "".join(
                    f"<td>{cell_symbol(str(fact_row.get(c, '')))}</td>"
                    for c in trimmed_months
                )
                tbody_parts.append(
                    f'<tr class="fact-row">'
                    f'<td class="work-name">{work_name}</td>'
                    f'<td class="type-cell">Факт</td>'
                    f'{fact_cells}</tr>'
                )

        if not tbody_parts:
            continue

        tbody = "<tbody>" + "".join(tbody_parts) + "</tbody>"
        blocks.append(
            f'<div class="prj-block">'
            f'<div class="prj-block-title">{prj_display}</div>'
            f'<table class="status-table">{colgroup}{thead}{tbody}</table>'
            f'</div>'
        )

    full_html = """<style>
.prj-block { margin-bottom: 28px; }
.prj-block-title {
    font-size: 0.92em; font-weight: 700; color: #ECF0F1;
    background: #2C3E50; padding: 7px 12px;
    border-radius: 6px 6px 0 0; border-bottom: 2px solid #1A252F;
}
.status-table { border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 0.78em; border-radius: 0 0 6px 6px; overflow: hidden; }
.status-table th { background: #34495E; color: #fff; text-align: center; padding: 3px 2px; overflow: hidden; }
.status-table .year-th { background: #2C3E50; }
.status-table .plan-row { background: #EBF5FB; }
.status-table .fact-row { background: #FFFFFF; }
.status-table .plan-row td, .status-table .fact-row td { color: #2C3E50; }
.status-table td { padding: 2px 2px; text-align: center; border: 1px solid #E8E8E8; overflow: hidden; }
.status-table td.work-name { text-align: left; white-space: normal; word-break: break-word; padding-left: 5px; }
.status-table td.type-cell { color: #7F8C8D; font-size: 0.85em; }
.dot  { color: #27AE60; }
.star { color: #F39C12; }
</style>
""" + "\n".join(blocks)

    st.markdown(full_html, unsafe_allow_html=True)
