"""
Page 6 — Project Drill-Down
Detailed view of a single project: KPI, Gantt, Milestones, Finance, Team.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Optional

st.set_page_config(page_title="Projects", page_icon="🔍", layout="wide")

from auth import render_sidebar_user, require_auth, require_role
from data.loader import (
    STATUS_COLORS, STATUS_EMOJI,
    load_prj_list, load_prj_status, load_prj_money, load_prj_team,
    get_finance_per_project,
    _find_col, parse_date_range, _parse_month_label,
)

authenticator = require_auth()
render_sidebar_user(authenticator)
require_role(["admin"])

MONTH_NAMES = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
               "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

PRIORITY_COLORS = {"Высокий": "#E74C3C", "Средний": "#F39C12", "Низкий": "#95A5A6"}

ROLE_LABELS = {"A": "РП (руководитель)", "S": "Участник", "БА": "Бизнес-аналитик"}

# ── Load data ──────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    prj    = load_prj_list()
    status = load_prj_status()
    money  = load_prj_money()
    team   = load_prj_team()
    fin_df = get_finance_per_project()

if prj.empty:
    st.error("Нет данных из 01.PRJ_LIST.")
    st.stop()

code_col     = _find_col(prj, ["Код проекта", "Код", "CODE"])
name_col     = _find_col(prj, ["Сокращенное название проекта", "Сокращённое название проекта", "Название"])
status_col   = _find_col(prj, ["Текущий статус", "Статус"])
period_col   = _find_col(prj, ["Плановый срок", "Срок"])
priority_col = _find_col(prj, ["Приоритет", "Priority"])
desc_col     = _find_col(prj, ["Описание системы", "Описание цели", "Описание", "Цель"])

# ── Project selector ──────────────────────────────────────────────────────────
code = st.query_params.get("project", "").strip()

if not code:
    all_codes = prj[code_col].dropna().tolist() if code_col else []
    prj_idx   = prj.set_index(code_col) if code_col else pd.DataFrame()

    def _fmt_option(c: str) -> str:
        if name_col and not prj_idx.empty and c in prj_idx.index:
            nm = str(prj_idx.loc[c, name_col]).strip()
            return f"{c} — {nm}" if nm else c
        return c

    code = st.selectbox(
        "Выберите проект",
        options=all_codes,
        format_func=_fmt_option,
    )
    if not code:
        st.stop()

# ── Look up project row ────────────────────────────────────────────────────────
prj_row: Optional[pd.Series] = None
if code_col and code in prj[code_col].values:
    prj_row = prj[prj[code_col] == code].iloc[0]

if prj_row is None:
    st.error(f"Проект «{code}» не найден.")
    st.stop()

name     = str(prj_row.get(name_col,     "") or "").strip() if name_col     else ""
status_v = str(prj_row.get(status_col,   "") or "").strip() if status_col   else ""
period   = str(prj_row.get(period_col,   "") or "").strip() if period_col   else ""
priority = str(prj_row.get(priority_col, "") or "").strip() if priority_col else ""
desc     = str(prj_row.get(desc_col,     "") or "").strip() if desc_col     else ""

color      = STATUS_COLORS.get(status_v, "#95A5A6")
emoji_st   = STATUS_EMOJI.get(status_v,  "⚪")
prio_color = PRIORITY_COLORS.get(priority, "#BDC3C7")

# ── Navigation ────────────────────────────────────────────────────────────────
st.page_link("pages/1_Index.py", label="← Портфель проектов", icon="📋")

# ── Page header ───────────────────────────────────────────────────────────────
prio_html = (
    f'<span style="font-size:0.75em;font-weight:700;padding:3px 10px;'
    f'border-radius:20px;background:{prio_color};color:#fff;white-space:nowrap;">'
    f'{priority}</span>'
) if priority else ""

desc_line = f'<p style="margin:6px 0 0 0;font-size:0.85em;color:#606060;">{desc}</p>' if desc else ""
period_line = f'<div style="margin-top:6px;font-size:0.8em;color:#7f8c8d;">📅 {period}</div>' if period else ""

st.markdown(f"""
<div style="
    background:#ffffff;border-radius:12px;padding:18px 24px;
    box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:20px;
    border-left:6px solid {color}
">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <span style="font-size:0.75em;font-weight:700;color:#95a5a6;
                 letter-spacing:.05em;text-transform:uppercase;">{code}</span>
    <div style="display:flex;gap:8px;align-items:center;">
      {prio_html}
      <span style="font-size:0.75em;font-weight:600;padding:3px 10px;
                   border-radius:20px;background:{color};color:#fff;">{emoji_st} {status_v}</span>
    </div>
  </div>
  <h2 style="margin:0;font-size:1.3em;color:#2c3e50;">{name}</h2>
  {desc_line}
  {period_line}
</div>
""", unsafe_allow_html=True)

# ── KPI (5 метрик) ────────────────────────────────────────────────────────────
fin_idx = fin_df.set_index("Код") if not fin_df.empty else pd.DataFrame()

budget = plan = fact = dev = unpaid = 0.0
if not fin_idx.empty and code in fin_idx.index:
    fr     = fin_idx.loc[code]
    budget = float(fr.get("Бюджет",      0) or 0)
    plan   = float(fr.get("План_оплат",  0) or 0)
    fact   = float(fr.get("Факт_оплат",  0) or 0)
    dev    = float(fr.get("Отклонение",  0) or 0)
    unpaid = float(fr.get("Не_оплачено", 0) or 0)

exec_pct = fact / plan * 100 if plan else 0


def fmt_mln(v: float) -> str:
    return f"{v / 1_000_000:.2f} млн ₽" if v else "—"


k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Бюджет 2026",  fmt_mln(budget))
k2.metric("Факт оплат",   fmt_mln(fact))
k3.metric("Отклонение",   fmt_mln(dev))
k4.metric("% исполнения", f"{exec_pct:.1f}%")
k5.metric("Не оплачено",  fmt_mln(unpaid))

st.divider()

# ── Gantt ─────────────────────────────────────────────────────────────────────
st.subheader("📅 Диаграмма Ганта")

_FIXED_STATUS_COLS = {"№", "Код проекта", "Название работы", "col3", "Тип", "Доп. описание", "Срок"}
month_cols: list[str] = (
    [c for c in status.columns if c not in _FIXED_STATUS_COLS]
    if not status.empty else []
)
month_dates: list[Optional[pd.Timestamp]] = [_parse_month_label(c) for c in month_cols]


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
    end_base = (
        month_dates[last_idx]
        if (last_idx is not None and month_dates[last_idx] is not None)
        else start
    )
    try:
        end = end_base + pd.DateOffset(months=1)
    except Exception:
        end = end_base
    return start, end


gantt_rows = []

start_dt, end_dt = parse_date_range(period)
if start_dt is None:
    start_dt = pd.Timestamp("2025-01-01")
if end_dt is None:
    end_dt = pd.Timestamp("2026-12-31")

label = f"{code} — {name}" if name else code
gantt_rows.append({
    "Задача":    label,
    "Начало":    start_dt,
    "Конец":     end_dt,
    "Тип_бар":  "Проект",
    "Цвет_ключ": status_v,
})

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
        })

if gantt_rows:
    gantt_df = pd.DataFrame(gantt_rows)
    gantt_df = gantt_df.dropna(subset=["Начало", "Конец"])
    gantt_df = gantt_df[gantt_df["Начало"] < gantt_df["Конец"]]

    if not gantt_df.empty:
        color_map  = {**STATUS_COLORS, "Работа": "#AAAAAA", "": "#BDC3C7"}
        task_order = gantt_df["Задача"].tolist()

        fig = px.timeline(
            gantt_df,
            x_start="Начало",
            x_end="Конец",
            y="Задача",
            color="Цвет_ключ",
            color_discrete_map=color_map,
        )
        fig.update_yaxes(
            categoryorder="array",
            categoryarray=task_order[::-1],
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
            height=max(200, len(gantt_df) * 28 + 80),
            xaxis_title="",
            yaxis_title="",
            legend_title="Статус",
            margin=dict(l=0, r=0, t=10, b=50),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных о сроках для построения Ганта.")
else:
    st.info("Нет данных о вехах для этого проекта.")

st.divider()

# ── Milestone table ────────────────────────────────────────────────────────────
st.subheader("📋 Исполнение вех")

if status.empty:
    st.info("Данные из 03.PRJ_STATUS недоступны.")
else:
    prj_status_rows = status[status["Код проекта"] == code]
    if prj_status_rows.empty:
        st.info("Нет данных о вехах для этого проекта.")
    else:
        # Trim month cols to non-empty range
        first_non_empty_idx: Optional[int] = None
        last_non_empty_idx:  Optional[int] = None
        for i, col in enumerate(month_cols):
            if col in prj_status_rows.columns and prj_status_rows[col].replace("", None).notna().any():
                if first_non_empty_idx is None:
                    first_non_empty_idx = i
                last_non_empty_idx = i

        trimmed_months = (
            month_cols[first_non_empty_idx : last_non_empty_idx + 1]
            if first_non_empty_idx is not None
            else month_cols
        )

        if not trimmed_months:
            st.info("Нет месячных данных для этого проекта.")
        else:
            year_headers: dict[str, int] = {}
            month_labels: list[str] = []
            for col in trimmed_months:
                parts = col.split("_", 1)
                if len(parts) == 2:
                    yr, mo = parts
                    year_headers[yr] = year_headers.get(yr, 0) + 1
                    month_labels.append(mo)
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

            n_month   = len(trimmed_months)
            month_pct = round(75 / n_month, 2) if n_month else 3
            colgroup  = (
                '<colgroup>'
                '<col style="width:20%">'
                '<col style="width:5%">'
                + f'<col style="width:{month_pct}%">' * n_month
                + '</colgroup>'
            )

            year_row_html  = "".join(
                f'<th class="year-th" colspan="{cs}">{yl}</th>'
                for yl, cs in year_headers.items()
            )
            month_row_html = "".join(f"<th>{m}</th>" for m in month_labels)

            thead = (
                '<thead>'
                f'<tr><th class="year-th" colspan="2"></th>{year_row_html}</tr>'
                f'<tr><th style="text-align:left;">Работа</th><th>Тип</th>{month_row_html}</tr>'
                '</thead>'
            )

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

            if tbody_parts:
                tbody = "<tbody>" + "".join(tbody_parts) + "</tbody>"
                milestone_html = f"""<style>
.status-table {{ border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 0.78em; border-radius: 0 0 6px 6px; overflow: hidden; }}
.status-table th {{ background: #34495E; color: #fff; text-align: center; padding: 3px 2px; overflow: hidden; }}
.status-table .year-th {{ background: #2C3E50; }}
.status-table .plan-row {{ background: #EBF5FB; }}
.status-table .fact-row {{ background: #FFFFFF; }}
.status-table .plan-row td, .status-table .fact-row td {{ color: #2C3E50; }}
.status-table td {{ padding: 2px 2px; text-align: center; border: 1px solid #E8E8E8; overflow: hidden; }}
.status-table td.work-name {{ text-align: left; white-space: normal; word-break: break-word; padding-left: 5px; }}
.status-table td.type-cell {{ color: #7F8C8D; font-size: 0.85em; }}
.dot  {{ color: #27AE60; }}
.star {{ color: #F39C12; }}
</style>
<table class="status-table">{colgroup}{thead}{tbody}</table>"""
                st.markdown(milestone_html, unsafe_allow_html=True)
            else:
                st.info("Нет вех с данными плана/факта.")

st.divider()

# ── Finance ────────────────────────────────────────────────────────────────────
st.subheader("💰 Финансы")

money_prj = money[money["Код проекта"] == code].copy() if not money.empty else pd.DataFrame()

if money_prj.empty:
    st.info("Нет финансовых данных для этого проекта.")
else:
    # Grouped bar: monthly plan vs fact
    detail    = money_prj[~money_prj["is_итого"]]
    plan_vals = [detail[f"{m}_план"].sum() / 1_000 for m in MONTH_NAMES]
    fact_vals = [detail[f"{m}_факт"].sum() / 1_000 for m in MONTH_NAMES]

    fact_colors = ["#2ECC71" if f <= p else "#E74C3C" for f, p in zip(fact_vals, plan_vals)]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name="План", x=MONTH_NAMES, y=plan_vals,
        marker_color="#3498DB", opacity=0.75,
    ))
    fig_bar.add_trace(go.Bar(
        name="Факт", x=MONTH_NAMES, y=fact_vals,
        marker_color=fact_colors,
    ))
    fig_bar.update_layout(
        barmode="group",
        height=260,
        yaxis_title="тыс. ₽",
        title="Помесячно: план vs факт, тыс. ₽",
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Detail table
    def _fmt_k(v) -> str:
        try:
            f = float(v)
            return f"{f / 1000:.1f}" if f != 0 else ""
        except (ValueError, TypeError):
            return ""

    def render_project_table(proj_df: pd.DataFrame) -> str:
        cg = (
            '<colgroup>'
            '<col style="width:13%">'
            '<col style="width:6%">'
            + '<col style="width:2.8%">' * 24
            + '<col style="width:4.6%">' * 3
            + '</colgroup>'
        )
        month_ths = "".join(f'<th>{m}.п</th><th>{m}.ф</th>' for m in MONTH_NAMES)
        thead = (
            "<thead><tr>"
            '<th class="lbl">Статья</th><th>Бюджет</th>'
            + month_ths
            + "<th>Ит.п</th><th>Ит.ф</th><th>Откл.</th>"
            "</tr></thead>"
        )
        tbody_rows = []
        for _, row in proj_df.iterrows():
            is_total = bool(row.get("is_итого", False))
            tr_cls   = ' class="ft-total"' if is_total else ""
            month_tds = []
            for m in MONTH_NAMES:
                p_val = float(row.get(f"{m}_план", 0) or 0)
                f_val = float(row.get(f"{m}_факт", 0) or 0)
                if is_total:
                    plan_cls = fact_cls = ""
                else:
                    plan_cls = ' class="ft-plan"'
                    if f_val == 0 and p_val == 0:
                        fact_cls = ' class="ft-zero"'
                    elif f_val <= p_val:
                        fact_cls = ' class="ft-ok"'
                    else:
                        fact_cls = ' class="ft-bad"'
                month_tds.append(
                    f'<td{plan_cls}>{_fmt_k(p_val)}</td>'
                    f'<td{fact_cls}>{_fmt_k(f_val)}</td>'
                )
            tbody_rows.append(
                f"<tr{tr_cls}>"
                f'<td class="lbl">{row.get("Статья", "")}</td>'
                f"<td>{_fmt_k(row.get('Бюджет_2026', 0))}</td>"
                + "".join(month_tds)
                + f"<td>{_fmt_k(row.get('План_оплат', 0))}</td>"
                + f"<td>{_fmt_k(row.get('Факт_оплат', 0))}</td>"
                + f"<td>{_fmt_k(row.get('Отклонение', 0))}</td>"
                "</tr>"
            )
        tbody = "<tbody>" + "\n".join(tbody_rows) + "</tbody>"
        return (
            '<div class="fin-wrap">'
            f'<table class="fin-table">{cg}{thead}{tbody}</table>'
            '</div>'
        )

    st.markdown("""<style>
.fin-wrap {
    width:100%;margin-bottom:12px;border:1px solid #ddd;
    border-radius:6px;box-sizing:border-box;overflow:hidden;
}
.fin-table {
    border-collapse:collapse;width:100%;
    table-layout:fixed;font-size:0.78em;background:#ffffff;
}
.fin-table th {
    background:#1a3a5c;color:#fff !important;padding:4px 3px;
    text-align:right;white-space:nowrap;overflow:hidden;
    font-weight:600;border:1px solid #12294a;
}
.fin-table th.lbl { text-align:left; }
.fin-table td {
    padding:3px 3px;color:#1a1a1a !important;border:1px solid #e8e8e8;
    text-align:right;white-space:nowrap;overflow:hidden;background:#ffffff;
}
.fin-table td.lbl { text-align:left;white-space:normal;word-break:break-word; }
.fin-table tr.ft-total td { background:#2c3e50 !important;color:#ffffff !important;font-weight:700; }
.fin-table td.ft-plan { background:#dbeeff !important; }
.fin-table td.ft-ok   { background:#d4f0dc !important; }
.fin-table td.ft-bad  { background:#fdd9d7 !important; }
.fin-table td.ft-zero { background:#f5f5f5 !important; }
</style>""", unsafe_allow_html=True)

    st.markdown(render_project_table(money_prj), unsafe_allow_html=True)
    st.caption("Числа в тыс. ₽. Факт-ячейки: зелёный — факт ≤ плана, красный — факт превысил план.")

st.divider()

# ── Team ───────────────────────────────────────────────────────────────────────
st.subheader("👥 Команда проекта")

if team.empty:
    st.info("Нет данных о команде.")
else:
    prj_team_rows = team[team["Код проекта"] == code]
    if prj_team_rows.empty:
        st.info("Нет данных о команде для этого проекта.")
    else:
        emp_cols = [c for c in team.columns if c not in ("Код проекта", "Название")]
        row_data = prj_team_rows.iloc[0]
        members  = [
            {
                "Сотрудник": emp,
                "Роль": ROLE_LABELS.get(str(row_data[emp]).strip(), str(row_data[emp]).strip()),
            }
            for emp in emp_cols
            if emp in row_data and str(row_data[emp]).strip()
        ]
        if members:
            st.dataframe(pd.DataFrame(members), use_container_width=True, hide_index=True)
        else:
            st.info("Нет участников для этого проекта.")
