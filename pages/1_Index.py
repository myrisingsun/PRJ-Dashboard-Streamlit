"""
Page 1 — Project Portfolio Index
Project cards + KPI metrics + summary table at the bottom
"""
import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Index — Portfolio", page_icon="📋", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import (
    STATUS_COLORS, STATUS_EMOJI,
    load_prj_list, get_finance_per_project, get_pm_per_project, _find_col,
)

authenticator = require_auth()
render_sidebar_user(authenticator)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Equal-height Streamlit columns */
div[data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
    gap: 16px !important;
    margin-bottom: 16px !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
    padding: 0 !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div > div[data-testid="stVerticalBlock"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
div[data-testid="stHorizontalBlock"] div[data-testid="stMarkdownContainer"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
/* Direct child of markdown container (p or div wrapping the HTML) */
div[data-testid="stHorizontalBlock"] div[data-testid="stMarkdownContainer"] > * {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    margin: 0 !important;
}

/* Card fills column */
.prj-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 16px 18px 14px 18px;
    border-left: 6px solid #95A5A6;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    flex: 1;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    font-family: inherit;
    height: 100%;
}
.prj-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}
.prj-code {
    font-size: 0.75em;
    font-weight: 700;
    color: #95a5a6;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.prj-badge {
    font-size: 0.68em;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 20px;
    color: white;
    white-space: nowrap;
}
.prj-name {
    font-size: 0.97em;
    font-weight: 700;
    color: #2c3e50;
    line-height: 1.35;
    margin-bottom: 5px;
}
.prj-meta {
    font-size: 0.78em;
    color: #7f8c8d;
    margin-bottom: 4px;
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
}
.prj-desc {
    flex: 1;
    min-height: 3.5em;
    margin: 6px 0 10px 0;
    overflow: hidden;
}
.prj-desc-text {
    font-size: 0.8em;
    color: #606060;
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.prj-finance {
    display: flex;
    gap: 0;
    border: 1px solid #ecf0f1;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 10px;
    flex-shrink: 0;
}
.prj-fin-cell {
    flex: 1;
    padding: 5px 8px;
    text-align: center;
    border-right: 1px solid #ecf0f1;
    background: #f9fafb;
}
.prj-fin-cell:last-child { border-right: none; }
.prj-fin-label {
    font-size: 0.62em;
    color: #95a5a6;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 600;
}
.prj-fin-value {
    font-size: 0.82em;
    font-weight: 700;
    color: #2c3e50;
    white-space: nowrap;
}
.prj-fin-value.fact  { color: #27ae60; }
.prj-fin-value.over  { color: #e74c3c; }
.prj-progress-wrap {
    background: #ecf0f1;
    border-radius: 4px;
    height: 5px;
    margin: 3px 0 0 0;
    overflow: hidden;
}
.prj-progress-bar {
    height: 100%;
    border-radius: 4px;
}
.prj-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: auto;
    padding-top: 4px;
}
.prj-links {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}
.prj-link {
    font-size: 0.74em;
    padding: 2px 9px;
    border-radius: 5px;
    background: #f0f3f4;
    color: #2980b9;
    text-decoration: none;
    border: 1px solid #dce3e8;
    font-weight: 500;
}
.prj-link:hover { background: #dce3e8; }
.prj-launched {
    font-size: 0.68em;
    padding: 2px 8px;
    border-radius: 10px;
    background: #eafaf1;
    color: #27ae60;
    border: 1px solid #a9dfbf;
    font-weight: 600;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    prj      = load_prj_list()
    fin_df   = get_finance_per_project()
    pm_map   = get_pm_per_project()

if prj.empty:
    st.error("Не удалось загрузить данные из листа 01.PRJ_LIST.")
    st.stop()

# ── Map columns ───────────────────────────────────────────────────────────────
code_col     = _find_col(prj, ["Код проекта", "Код", "CODE"])
name_col     = _find_col(prj, ["Сокращенное название проекта", "Сокращённое название проекта", "Название"])
status_col   = _find_col(prj, ["Текущий статус", "Статус"])
period_col   = _find_col(prj, ["Плановый срок", "Срок"])
desc_col     = _find_col(prj, ["Описание системы", "Описание цели", "Описание", "Цель"])
priority_col = _find_col(prj, ["Приоритет", "Priority"])
launched_col = _find_col(prj, ["Проектное задание подписано?", "Запущен проект ?", "Запущен проект?", "Запущен"])
bitrix_col   = _find_col(prj, ["Проектная область в Bitrix", "Запускен проект в Bitrix", "Ссылка в Bitrix"])
pdf_col      = _find_col(prj, ["Ссылка на приказ в Bitrix24 (PDF)", "Приказ PDF"])
prod_col     = _find_col(prj, ["Ссылка на систему PROD", "PROD"])
test_col     = _find_col(prj, ["Ссылка на систему TEST \\ STAGE", "Ссылка на систему TEST", "TEST"])

PRIORITY_ORDER  = {"Высокий": 0, "Средний": 1, "Низкий": 2}
PRIORITY_COLORS = {"Высокий": "#E74C3C", "Средний": "#F39C12", "Низкий": "#95A5A6"}

# Finance lookup: project code → row
fin_idx = fin_df.set_index("Код") if not fin_df.empty else pd.DataFrame()

# ── KPI ───────────────────────────────────────────────────────────────────────
st.title("📋 Портфель проектов")

status_counts = prj[status_col].value_counts() if status_col else pd.Series(dtype=int)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Всего проектов",  len(prj))
k2.metric("По плану 🟢",     status_counts.get("По плану",      0))
k3.metric("Есть риски 🔴",   status_counts.get("Есть риски",    0))
k4.metric("Отстает 🟡",      status_counts.get("Отстает",       0))
k5.metric("Приостановлен ⚫", status_counts.get("Приостановлен", 0))

# ── Sidebar filters ───────────────────────────────────────────────────────────
all_codes    = prj[code_col].dropna().tolist()          if code_col    else []
all_statuses = sorted(prj[status_col].dropna().unique()) if status_col else []

with st.sidebar:
    st.divider()
    st.markdown("### Фильтры")

    # Projects
    st.caption("Проекты")
    if st.button("Все проекты", use_container_width=True, key="btn_all_codes"):
        st.session_state["sel_codes"] = all_codes
    sel_codes = st.multiselect(
        "Проекты",
        options=all_codes,
        default=st.session_state.get("sel_codes", all_codes),
        key="sel_codes",
        label_visibility="collapsed",
    )

    # Statuses
    st.caption("Статус")
    if st.button("Все статусы", use_container_width=True, key="btn_all_statuses"):
        st.session_state["sel_statuses"] = all_statuses
    sel_statuses = st.multiselect(
        "Статус",
        options=all_statuses,
        default=st.session_state.get("sel_statuses", all_statuses),
        key="sel_statuses",
        label_visibility="collapsed",
    )

    # Priorities
    all_priorities = ["Высокий", "Средний", "Низкий"]
    st.caption("Приоритет")
    if st.button("Все приоритеты", use_container_width=True, key="btn_all_priorities"):
        st.session_state["sel_priorities"] = all_priorities
    sel_priorities = st.multiselect(
        "Приоритет",
        options=all_priorities,
        default=st.session_state.get("sel_priorities", all_priorities),
        key="sel_priorities",
        label_visibility="collapsed",
    )

    # Cards per row
    st.caption("Карточек в ряду")
    cards_per_row = st.select_slider(
        "Карточек в ряду", options=[1, 2, 3], value=3,
        label_visibility="collapsed",
    )

st.divider()

# Apply filters
filtered = prj.copy()
if sel_codes and code_col:
    filtered = filtered[filtered[code_col].isin(sel_codes)]
if sel_statuses and status_col:
    filtered = filtered[filtered[status_col].isin(sel_statuses)]
if sel_priorities and priority_col:
    filtered = filtered[filtered[priority_col].isin(sel_priorities)]

# Sort by priority: Высокий → Средний → Низкий → (пусто)
if priority_col and priority_col in filtered.columns:
    filtered = filtered.copy()
    filtered["_prio_order"] = filtered[priority_col].map(PRIORITY_ORDER).fillna(99)
    filtered = filtered.sort_values("_prio_order").drop(columns=["_prio_order"])

# ── Portfolio finance summary ──────────────────────────────────────────────────
if not fin_df.empty:
    vis_codes   = filtered[code_col].tolist() if code_col else []
    fin_visible = fin_df[fin_df["Код"].isin(vis_codes)] if vis_codes else fin_df

    p_budget = fin_visible["Бюджет"].sum()
    p_plan   = fin_visible["План_оплат"].sum()
    p_fact   = fin_visible["Факт_оплат"].sum()
    p_unpaid = fin_visible["Не_оплачено"].sum()

    plan_pct = min(p_fact / p_plan * 100, 100) if p_plan else 0
    budg_pct = min(p_fact / p_budget * 100, 100) if p_budget else 0

    def fmt_rub(v):
        if v >= 1_000_000:
            return f"{v / 1_000_000:.1f} млн ₽"
        if v > 0:
            return f"{v / 1_000:.0f} тыс ₽"
        return "—"

    bar_color = "#2ECC71" if p_fact <= p_plan else "#E74C3C"

    st.markdown(f"""
<div style="
    background:#ffffff;border-radius:12px;padding:18px 24px;
    box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:20px;
    border-left:6px solid #3498DB;
">
  <div style="font-size:0.78em;font-weight:700;color:#3498db;
              text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px;">
    Портфель проектов — финансы
  </div>
  <div style="display:flex;gap:0;border:1px solid #ecf0f1;border-radius:8px;overflow:hidden;margin-bottom:14px;">
    <div style="flex:1;padding:10px 14px;background:#f9fafb;border-right:1px solid #ecf0f1;">
      <div style="font-size:0.65em;color:#95a5a6;text-transform:uppercase;font-weight:600;letter-spacing:.04em;">Бюджет</div>
      <div style="font-size:1.15em;font-weight:700;color:#2c3e50;">{fmt_rub(p_budget)}</div>
    </div>
    <div style="flex:1;padding:10px 14px;background:#f9fafb;border-right:1px solid #ecf0f1;">
      <div style="font-size:0.65em;color:#95a5a6;text-transform:uppercase;font-weight:600;letter-spacing:.04em;">План оплат</div>
      <div style="font-size:1.15em;font-weight:700;color:#2c3e50;">{fmt_rub(p_plan)}</div>
    </div>
    <div style="flex:1;padding:10px 14px;background:#f9fafb;border-right:1px solid #ecf0f1;">
      <div style="font-size:0.65em;color:#95a5a6;text-transform:uppercase;font-weight:600;letter-spacing:.04em;">Факт оплат</div>
      <div style="font-size:1.15em;font-weight:700;color:{bar_color};">{fmt_rub(p_fact)}</div>
    </div>
    <div style="flex:1;padding:10px 14px;background:#f9fafb;">
      <div style="font-size:0.65em;color:#95a5a6;text-transform:uppercase;font-weight:600;letter-spacing:.04em;">Не оплачено</div>
      <div style="font-size:1.15em;font-weight:700;color:#e67e22;">{fmt_rub(p_unpaid)}</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:0.75em;color:#7f8c8d;white-space:nowrap;">
      Исполнение плана: <b>{plan_pct:.0f}%</b>
    </div>
    <div style="flex:1;background:#ecf0f1;border-radius:6px;height:8px;overflow:hidden;">
      <div style="width:{plan_pct:.0f}%;height:100%;background:{bar_color};border-radius:6px;transition:width .4s;"></div>
    </div>
    <div style="font-size:0.75em;color:#7f8c8d;white-space:nowrap;">
      {len(vis_codes)} проект{'ов' if len(vis_codes) not in (1,) else 'а' if len(vis_codes)==1 else 'ов'}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Card builder ──────────────────────────────────────────────────────────────
def fmt_mln(v: float) -> str:
    if v == 0:
        return "—"
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f} млн"
    return f"{v/1_000:.0f} тыс"

def project_card(row: pd.Series) -> str:
    code     = str(row.get(code_col,     "") or "").strip() if code_col     else ""
    name     = str(row.get(name_col,     "") or "").strip() if name_col     else ""
    status   = str(row.get(status_col,   "") or "").strip() if status_col   else ""
    period   = str(row.get(period_col,   "") or "").strip() if period_col   else ""
    desc     = str(row.get(desc_col,     "") or "").strip() if desc_col     else ""
    launched = str(row.get(launched_col, "") or "").strip() if launched_col else ""

    priority = str(row.get(priority_col, "") or "").strip() if priority_col else ""

    color      = STATUS_COLORS.get(status, "#95A5A6")
    emoji      = STATUS_EMOJI.get(status,  "⚪")
    pm         = pm_map.get(code, "—")
    prio_color = PRIORITY_COLORS.get(priority, "#BDC3C7")

    # Finance
    budget = plan = fact = exec_p = 0.0
    if not fin_idx.empty and code in fin_idx.index:
        fr     = fin_idx.loc[code]
        budget = float(fr["Бюджет"])     if "Бюджет"     in fr else 0
        plan   = float(fr["План_оплат"]) if "План_оплат" in fr else 0
        fact   = float(fr["Факт_оплат"]) if "Факт_оплат" in fr else 0
        exec_p = (fact / plan * 100) if plan else 0

    fact_cls  = "fact" if fact <= plan else "over"
    bar_pct   = min(exec_p, 100)
    bar_color = "#2ECC71" if fact <= plan else "#E74C3C"

    finance_html = f"""
<div class="prj-finance">
  <div class="prj-fin-cell">
    <div class="prj-fin-label">Бюджет</div>
    <div class="prj-fin-value">{fmt_mln(budget)}</div>
  </div>
  <div class="prj-fin-cell">
    <div class="prj-fin-label">План</div>
    <div class="prj-fin-value">{fmt_mln(plan)}</div>
  </div>
  <div class="prj-fin-cell">
    <div class="prj-fin-label">Факт</div>
    <div class="prj-fin-value {fact_cls}">{fmt_mln(fact)}</div>
    <div class="prj-progress-wrap">
      <div class="prj-progress-bar" style="width:{bar_pct:.0f}%;background:{bar_color}"></div>
    </div>
  </div>
</div>""" if budget or plan or fact else ""

    # Links
    def lnk(url, label):
        u = str(url or "").strip()
        return f'<a class="prj-link" href="{u}" target="_blank">{label}</a>' if u.startswith("http") else ""

    links_html = "".join(filter(None, [
        lnk(row.get(bitrix_col, "") if bitrix_col else "", "📋 Bitrix"),
        lnk(row.get(pdf_col,    "") if pdf_col    else "", "📎 Приказ"),
        lnk(row.get(prod_col,   "") if prod_col   else "", "🔗 PROD"),
        lnk(row.get(test_col,   "") if test_col   else "", "🧪 TEST"),
    ]))

    launched_html = '<span class="prj-launched">✅ Запущен</span>' \
        if launched.upper() in ("ДА", "YES", "TRUE", "1") else ""

    period_html = f'<span>📅 {period}</span>' if period else ""
    pm_html     = f'<span>👤 {pm}</span>'     if pm and pm != "—" else ""
    meta_html   = f'<div class="prj-meta">{period_html}{pm_html}</div>' \
        if (period_html or pm_html) else ""

    desc_html = f'<div class="prj-desc"><div class="prj-desc-text">{desc}</div></div>'

    footer_html = ""
    if links_html or launched_html:
        footer_html = f"""
<div class="prj-footer">
  <div class="prj-links">{links_html}</div>
  {launched_html}
</div>"""

    prio_html = (
        f'<span style="font-size:0.65em;font-weight:700;padding:2px 8px;'
        f'border-radius:20px;background:{prio_color};color:#fff;white-space:nowrap;">'
        f'{priority}</span>'
    ) if priority else ""

    return f"""
<div class="prj-card" style="border-left-color:{color}">
  <div class="prj-card-top">
    <span class="prj-code">{code}</span>
    <div style="display:flex;gap:6px;align-items:center;">
      {prio_html}
      <span class="prj-badge" style="background:{color}">{emoji} {status}</span>
    </div>
  </div>
  <div class="prj-name">{name}</div>
  {meta_html}
  {desc_html}
  {finance_html}
  {footer_html}
</div>"""

# ── Render cards ──────────────────────────────────────────────────────────────
rows_iter = list(filtered.iterrows())
for i in range(0, len(rows_iter), cards_per_row):
    cols = st.columns(cards_per_row)
    for j, (_, row) in enumerate(rows_iter[i : i + cards_per_row]):
        with cols[j]:
            st.markdown(project_card(row), unsafe_allow_html=True)

if filtered.empty:
    st.info("Нет проектов с выбранным статусом.")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("Распределение по статусам")
    if status_col and not prj.empty:
        sc = prj[status_col].value_counts().reset_index()
        sc.columns = ["Статус", "Кол-во"]
        fig = px.pie(sc, names="Статус", values="Кол-во", color="Статус",
                     color_discrete_map=STATUS_COLORS, hole=0.4)
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

with c_right:
    st.subheader("Распределение по приоритетам")
    if priority_col and not prj.empty:
        pc = prj[priority_col].replace("", None).dropna().value_counts().reset_index()
        pc.columns = ["Приоритет", "Кол-во"]
        fig_p = px.pie(pc, names="Приоритет", values="Кол-во", color="Приоритет",
                       color_discrete_map=PRIORITY_COLORS, hole=0.4)
        fig_p.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_p, use_container_width=True)

st.subheader("Бюджет vs Факт оплат")
if not fin_df.empty:
    fin_melted = fin_df.melt(
        id_vars="Код", value_vars=["Бюджет", "План_оплат", "Факт_оплат"],
        var_name="Тип", value_name="Сумма"
    )
    fin_melted["Тип"] = fin_melted["Тип"].map(
        {"Бюджет": "Бюджет", "План_оплат": "План", "Факт_оплат": "Факт"}
    )
    fig2 = px.bar(
        fin_melted, x="Сумма", y="Код", color="Тип", orientation="h",
        color_discrete_map={"Бюджет": "#3498DB", "План": "#9B59B6", "Факт": "#2ECC71"},
        barmode="group",
    )
    fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0),
                       yaxis={"categoryorder": "total ascending"}, height=400)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Summary table ─────────────────────────────────────────────────────────────
st.subheader("Реестр проектов")
table_cols = [c for c in [code_col, name_col, priority_col, status_col, period_col, desc_col] if c]
table = filtered[table_cols].copy() if table_cols else filtered.copy()
if status_col and status_col in table.columns:
    table.insert(table.columns.get_loc(status_col), "🚦",
                 table[status_col].map(lambda s: STATUS_EMOJI.get(s, "⚪")))
row_height = 35
header_height = 38
st.dataframe(table, use_container_width=True, hide_index=True,
             height=header_height + row_height * len(table))
st.caption("Данные обновляются каждые 5 минут.")
