"""
Page 3 — Finances 2026
KPI cards, monthly plan/fact bar chart, detailed position table with cell notes
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Finance", page_icon="💰", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import load_prj_money

authenticator = require_auth()
render_sidebar_user(authenticator)

st.title("💰 Финансы 2026")

# ── RAW DATA INSPECTOR ────────────────────────────────────────────────────────
with st.expander("🔍 Диагностика: сырые строки из 05.PRJ_MONEY_2026", expanded=False):
    from data.loader import _load_raw
    raw = _load_raw("05.PRJ_MONEY_2026")
    inspect_code = st.text_input("Код для фильтра (столбец A)", value="PRMN.0001")
    show_all = st.checkbox("Показать все строки")
    matching = []
    for i, row in enumerate(raw):
        c0 = row[0].strip() if row else ""
        if show_all or c0 == inspect_code:
            matching.append({"#": i + 1, **{str(j): v for j, v in enumerate(row)}})
    if matching:
        st.dataframe(pd.DataFrame(matching).fillna(""), use_container_width=True)
        st.caption("# — номер строки в листе (1-based). Числа в заголовках — индексы столбцов (0-based).")
    else:
        st.info(f"Строк с кодом '{inspect_code}' в столбце A не найдено.")

st.divider()

# ── Load ─────────────────────────────────────────────────────────────────────
with st.spinner("Загрузка финансовых данных..."):
    money = load_prj_money()

if money.empty:
    st.error("Не удалось загрузить данные из листа 05.PRJ_MONEY_2026.")
    st.stop()

# ── Filters ──────────────────────────────────────────────────────────────────
products = ["Все"] + sorted(money["IT_продукт"].dropna().unique().tolist())
selected_product = st.selectbox("IT-продукт / Проект", products)

month_names = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
               "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

filtered = money.copy()
if selected_product != "Все":
    filtered = filtered[filtered["IT_продукт"] == selected_product]

is_total = filtered["Позиция"].str.strip().str.lower().str.startswith("итого") if "Позиция" in filtered.columns else pd.Series(False, index=filtered.index)
detail = filtered[~is_total]

# ── KPI cards ────────────────────────────────────────────────────────────────
budget = filtered["Бюджет_2026"].sum(skipna=True) if "Бюджет_2026" in filtered.columns else 0
fact   = filtered["Факт_оплат"].sum(skipna=True)  if "Факт_оплат"  in filtered.columns else 0
dev    = filtered["Отклонение"].sum(skipna=True)   if "Отклонение"  in filtered.columns else (budget - fact)
unpaid = filtered["Не_оплачено"].sum(skipna=True)  if "Не_оплачено" in filtered.columns else 0

def fmt(v):
    return f"{v / 1_000_000:.2f} млн ₽" if v else "—"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Бюджет 2026",       fmt(budget))
c2.metric("Оплачено (факт)",   fmt(fact))
c3.metric("Отклонение",        fmt(dev),    delta=f"{dev / budget * 100:.1f}%" if budget else None)
c4.metric("Запланировано, не оплачено", fmt(unpaid))

st.divider()

# ── Monthly plan / fact chart ────────────────────────────────────────────────
st.subheader("Помесячное исполнение")

plan_cols = [f"{m}_план" for m in month_names]
fact_cols = [f"{m}_факт" for m in month_names]

plan_vals = [detail[c].sum(skipna=True) if c in detail.columns else 0 for c in plan_cols]
fact_vals = [detail[c].sum(skipna=True) if c in detail.columns else 0 for c in fact_cols]

fig = go.Figure()
fig.add_trace(go.Bar(
    name="План",
    x=month_names,
    y=plan_vals,
    marker_color="#3498DB",
    opacity=0.85,
))
fig.add_trace(go.Bar(
    name="Факт",
    x=month_names,
    y=fact_vals,
    marker_color=[
        "#2ECC71" if f <= p else "#E74C3C"
        for f, p in zip(fact_vals, plan_vals)
    ],
))
fig.update_layout(
    barmode="group",
    xaxis_title="Месяц",
    yaxis_title="Сумма, ₽",
    legend_title="",
    margin=dict(l=0, r=0, t=10, b=0),
    height=350,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Detail table ─────────────────────────────────────────────────────────────
st.subheader("Детализация по позициям")

show_cols = ["IT_продукт", "Позиция", "Бюджет_2026"] + plan_cols + fact_cols + ["Факт_оплат", "Отклонение"]
show_cols = [c for c in show_cols if c in detail.columns]

if not detail.empty:
    display = detail[show_cols].copy()

    # Format numeric columns for readability
    num_cols = [c for c in show_cols if c not in ("IT_продукт", "Позиция")]
    for col in num_cols:
        display[col] = display[col].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) and x != 0 else ""
        )

    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("Нет данных по выбранному фильтру.")

st.caption("Зелёный — факт ≤ план. Красный — факт превысил план.")
