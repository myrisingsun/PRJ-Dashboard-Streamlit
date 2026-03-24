"""
Page 3 — Finances 2026
KPI cards → analytics charts (portfolio + per-project) → per-project tables.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Finance", page_icon="💰", layout="wide")

from auth import render_sidebar_user, require_auth, require_role
from data.loader import load_prj_money, load_prj_list, _find_col

authenticator = require_auth()
render_sidebar_user(authenticator)
require_role(["admin"])

st.title("💰 Финансы 2026")

MONTH_NAMES = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
               "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

# ── Load data ──────────────────────────────────────────────────────────────────
with st.spinner("Загрузка финансовых данных..."):
    money    = load_prj_money()
    prj_list = load_prj_list()

# ── Project metadata ───────────────────────────────────────────────────────────
code_col = _find_col(prj_list, ["Код проекта", "Код", "CODE"]) if not prj_list.empty else None
name_col = _find_col(prj_list, ["Сокращенное название проекта", "Сокращённое название проекта",
                                 "Название"]) if not prj_list.empty else None

code_to_name: dict[str, str] = {}
prj_order: list[str] = []

if not prj_list.empty and code_col:
    prj_order = prj_list[code_col].dropna().astype(str).str.strip().tolist()
    if name_col:
        for _, row in prj_list.iterrows():
            c = str(row[code_col]).strip()
            n = str(row[name_col]).strip()
            if c:
                code_to_name[c] = n

if not money.empty:
    all_codes_set = set(money["Код проекта"].dropna().unique().tolist())
    all_codes = [c for c in prj_order if c in all_codes_set] + \
                [c for c in all_codes_set if c not in set(prj_order)]
else:
    all_codes = []

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Фильтры")

    if st.button("Все проекты", use_container_width=True, key="fin_all"):
        st.session_state["fin_selected"] = all_codes[:]

    default_sel = st.session_state.get("fin_selected", all_codes)
    default_sel = [c for c in default_sel if c in all_codes]

    selected: list[str] = st.multiselect(
        "Проекты",
        options=all_codes,
        default=default_sel,
        format_func=lambda c: f"{c} — {code_to_name[c]}" if c in code_to_name else c,
    )
    st.session_state["fin_selected"] = selected

    st.divider()
    if st.button("🔄 Обновить данные", use_container_width=True, key="fin_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Early exit if no data ──────────────────────────────────────────────────────
if money.empty:
    st.error("Не удалось загрузить данные из листа 05.PRJ_MONEY_2026.")
    st.stop()

# ── Filtered data (single source of truth for KPIs and tables) ─────────────────
sel_set = set(selected)

ordered_codes  = [c for c in prj_order if c in sel_set] + \
                 [c for c in selected  if c not in set(prj_order)]
filtered_money = money[money["Код проекта"].isin(sel_set)]

# KPIs come from "Итого" rows of filtered_money — same data as the tables below
ft = filtered_money[filtered_money["is_итого"]]


def _sum(df: pd.DataFrame, col: str) -> float:
    return float(df[col].sum()) if not df.empty and col in df.columns else 0.0


budget   = _sum(ft, "Бюджет_2026")
plan_pay = _sum(ft, "План_оплат")
fact_pay = _sum(ft, "Факт_оплат")
dev      = _sum(ft, "Отклонение")
unpaid   = _sum(ft, "Не_оплачено")


def fmt_mln(v: float) -> str:
    return f"{v / 1_000_000:.2f} млн ₽" if v else "—"


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Бюджет 2026",            fmt_mln(budget))
c2.metric("Запланировано к оплате", fmt_mln(plan_pay))
c3.metric("Оплачено (факт)",        fmt_mln(fact_pay))
c4.metric("Отклонение",             fmt_mln(dev))
c5.metric("Не оплачено",            fmt_mln(unpaid))

st.divider()

if not selected:
    st.info("Выберите хотя бы один проект в боковой панели.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS: chart builders
# ══════════════════════════════════════════════════════════════════════════════

_CHART_LAYOUT = dict(
    margin=dict(l=10, r=10, t=30, b=10),
    plot_bgcolor="#ffffff",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(size=11),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(size=10)),
)


def make_portfolio_chart() -> go.Figure | None:
    """Horizontal grouped bar: Бюджет / План / Факт by project (from итого rows)."""
    df = (
        filtered_money[filtered_money["is_итого"]]
        .groupby("Код проекта")[["Бюджет_2026", "План_оплат", "Факт_оплат"]]
        .sum()
        .reset_index()
    )
    # preserve display order
    code_order = {c: i for i, c in enumerate(ordered_codes)}
    df["_ord"] = df["Код проекта"].map(code_order).fillna(999)
    df = df.sort_values("_ord").drop(columns="_ord")

    if df.empty:
        return None

    labels = [
        f"{r['Код проекта']} — {code_to_name[r['Код проекта']]}"
        if r["Код проекта"] in code_to_name else r["Код проекта"]
        for _, r in df.iterrows()
    ]

    def _m(vals):
        return [f"{v:.1f}" if v > 0 else "" for v in vals]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Бюджет", y=labels, x=df["Бюджет_2026"] / 1e6,
        orientation="h", marker_color="#3498DB", opacity=0.55,
        text=_m(df["Бюджет_2026"] / 1e6), textposition="outside", cliponaxis=False,
    ))
    fig.add_trace(go.Bar(
        name="План оплат", y=labels, x=df["План_оплат"] / 1e6,
        orientation="h", marker_color="#9B59B6", opacity=0.75,
        text=_m(df["План_оплат"] / 1e6), textposition="outside", cliponaxis=False,
    ))
    fig.add_trace(go.Bar(
        name="Факт оплат", y=labels, x=df["Факт_оплат"] / 1e6,
        orientation="h", marker_color="#2ECC71",
        text=_m(df["Факт_оплат"] / 1e6), textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        barmode="group",
        height=max(220, len(df) * 55 + 60),
        xaxis_title="млн ₽",
        title="Бюджет vs Факт по проектам",
    )
    fig.update_layout(margin_r=80)
    return fig


def make_monthly_bars_from(plan: list, fact: list, title: str) -> go.Figure:
    """Grouped bar chart from pre-computed plan/fact lists (тыс. ₽)."""
    fact_colors = ["#2ECC71" if f <= p else "#E74C3C" for f, p in zip(fact, plan)]

    def _t(vals):
        return [f"{v:.0f}" if v > 0 else "" for v in vals]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="План", x=MONTH_NAMES, y=plan,
        marker_color="#3498DB", opacity=0.75,
        text=_t(plan), textposition="outside", cliponaxis=False,
    ))
    fig.add_trace(go.Bar(
        name="Факт", x=MONTH_NAMES, y=fact,
        marker_color=fact_colors,
        text=_t(fact), textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        barmode="group",
        height=300,
        yaxis_title="тыс. ₽",
        title=title,
    )
    return fig




# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ANALYTICS  (single aggregate block for all selected projects)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Аналитика")

agg_df = filtered_money[~filtered_money["is_итого"]]  # non-total rows, all projects

# 1. Portfolio bar
port_fig = make_portfolio_chart()
if port_fig:
    st.plotly_chart(port_fig, use_container_width=True)

# 2. Budget donut by project
budg_by_prj = (
    agg_df.groupby("Код проекта")["Бюджет_2026"].sum()
    .pipe(lambda s: s[s > 0])
    .sort_values(ascending=False)
)
if not budg_by_prj.empty:
    labels_pie = [
        f"{c} — {code_to_name[c]}" if c in code_to_name else c
        for c in budg_by_prj.index
    ]
    donut_prj = go.Figure(go.Pie(
        labels=labels_pie,
        values=(budg_by_prj / 1_000).tolist(),
        hole=0.45,
        texttemplate="%{percent:.0%}<br>%{value:.0f} тыс",
        hovertemplate="%{label}: %{value:.1f} тыс. ₽<extra></extra>",
    ))
    donut_prj.update_layout(
        **_CHART_LAYOUT,
        height=350,
        title="Структура бюджета по проектам",
        legend=dict(orientation="v", font=dict(size=10), x=1.01, xanchor="left"),
        margin=dict(l=10, r=200, t=30, b=10),
    )
    st.plotly_chart(donut_prj, use_container_width=True)

# 3. Monthly bars (aggregate)
plan_agg = [agg_df[f"{m}_план"].sum() / 1_000 for m in MONTH_NAMES]
fact_agg = [agg_df[f"{m}_факт"].sum() / 1_000 for m in MONTH_NAMES]
st.plotly_chart(
    make_monthly_bars_from(plan_agg, fact_agg, "Помесячно: план vs факт, тыс. ₽"),
    use_container_width=True,
)


st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — TABLES
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Детализация по статьям")


def _fmt_k(v) -> str:
    """Format a number in thousands, no decimals. Returns '' for zero."""
    try:
        f = float(v)
        return f"{f / 1000:.0f}" if f != 0 else ""
    except (ValueError, TypeError):
        return ""


def render_project_table(proj_df: pd.DataFrame) -> str:
    """Return HTML string for one project's plan/fact table.
    table-layout:fixed + colgroup % widths → fits container width.
    """
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
        "</div>"
    )


# CSS — injected once
st.markdown("""
<style>
.fin-wrap {
    width: 100%; margin-bottom: 12px;
    border: 1px solid #ddd; border-radius: 6px;
    box-sizing: border-box; overflow: hidden;
}
.fin-table {
    border-collapse: collapse; width: 100%;
    table-layout: fixed; font-size: 0.78em; background: #ffffff;
}
.fin-table th {
    background: #1a3a5c; color: #fff !important;
    padding: 4px 3px; text-align: right;
    white-space: nowrap; overflow: hidden; font-weight: 600;
    border: 1px solid #12294a;
}
.fin-table th.lbl { text-align: left; }
.fin-table td {
    padding: 3px 3px; color: #1a1a1a !important;
    border: 1px solid #e8e8e8; text-align: right;
    white-space: nowrap; overflow: hidden; background: #ffffff;
}
.fin-table td.lbl {
    text-align: left; white-space: normal; word-break: break-word;
}
.fin-table tr.ft-total td {
    background: #2c3e50 !important; color: #ffffff !important; font-weight: 700;
}
.fin-table td.ft-plan { background: #dbeeff !important; }
.fin-table td.ft-ok   { background: #d4f0dc !important; }
.fin-table td.ft-bad  { background: #fdd9d7 !important; }
.fin-table td.ft-zero { background: #f5f5f5 !important; }
</style>
""", unsafe_allow_html=True)

for code in ordered_codes:
    proj_df = filtered_money[filtered_money["Код проекта"] == code]
    if proj_df.empty:
        continue

    name   = code_to_name.get(code, "")
    header = f"{code} — {name}" if name else code
    st.subheader(header)
    st.markdown(render_project_table(proj_df), unsafe_allow_html=True)

st.caption(
    "Числа в тыс. ₽.  "
    "Факт-ячейки: зелёный — факт ≤ плана, красный — факт превысил план."
)
