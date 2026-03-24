"""
Page 5 — Non-project / operational work (02.OPER_LIST)
"""
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Operations", page_icon="🔧", layout="wide")

from auth import render_sidebar_user, require_auth, require_role
from data.loader import STATUS_COLORS, STATUS_EMOJI, load_oper_list, _find_col

authenticator = require_auth()
render_sidebar_user(authenticator)
require_role(["admin"])

st.title("🔧 Внепроектная и операционная работа")

# ── Load ─────────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    oper = load_oper_list()

if oper.empty:
    st.error("Не удалось загрузить данные из листа 02.OPER_LIST.")
    st.stop()

# ── Key columns ───────────────────────────────────────────────────────────────
code_col   = _find_col(oper, ["Код", "КОД", "CODE"])
name_col   = _find_col(oper, ["Название", "Наименование"])
status_col = _find_col(oper, ["Текущий статус", "Статус", "Статус задачи"])
resp_col   = _find_col(oper, ["Ответственный", "Владелец"])
period_col = _find_col(oper, ["Срок", "Плановый срок"])

# ── KPI cards ─────────────────────────────────────────────────────────────────
total = len(oper)
status_counts = oper[status_col].value_counts() if status_col else {}

col1, col2, col3, col4 = st.columns(4)
col1.metric("Всего задач", total)
col2.metric("По плану 🟢",      status_counts.get("По плану", 0))
col3.metric("Есть риски 🔴",    status_counts.get("Есть риски", 0))
col4.metric("Приостановлено ⚫", status_counts.get("Приостановлен", 0))

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    if status_col:
        statuses = ["Все"] + sorted(oper[status_col].dropna().unique().tolist())
        sel_status = st.selectbox("Статус", statuses)
    else:
        sel_status = "Все"

with filter_col2:
    if resp_col:
        resps = ["Все"] + sorted(oper[resp_col].dropna().unique().tolist())
        sel_resp = st.selectbox("Ответственный", resps)
    else:
        sel_resp = "Все"

filtered = oper.copy()
if sel_status != "Все" and status_col:
    filtered = filtered[filtered[status_col] == sel_status]
if sel_resp != "Все" and resp_col:
    filtered = filtered[filtered[resp_col] == sel_resp]

# ── Table ─────────────────────────────────────────────────────────────────────
st.subheader(f"Задачи ({len(filtered)})")

display_cols = [c for c in [code_col, name_col, status_col, resp_col, period_col] if c]
display = filtered[display_cols].copy() if display_cols else filtered.copy()

if status_col and status_col in display.columns:
    display.insert(
        display.columns.get_loc(status_col),
        "🚦",
        display[status_col].map(lambda s: STATUS_EMOJI.get(s, "⚪")),
    )

st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()

# ── Status chart ──────────────────────────────────────────────────────────────
if status_col and status_col in oper.columns:
    st.subheader("Распределение по статусам")
    sc = oper[status_col].value_counts().reset_index()
    sc.columns = ["Статус", "Количество"]
    fig = px.pie(
        sc,
        names="Статус",
        values="Количество",
        color="Статус",
        color_discrete_map=STATUS_COLORS,
        hole=0.4,
    )
    fig.update_layout(margin=dict(t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ── Responsible workload ───────────────────────────────────────────────────────
if resp_col and resp_col in oper.columns:
    st.subheader("Нагрузка по ответственным")
    resp_counts = oper[resp_col].value_counts().reset_index()
    resp_counts.columns = ["Ответственный", "Задач"]
    fig2 = px.bar(
        resp_counts,
        x="Задач",
        y="Ответственный",
        orientation="h",
        color_discrete_sequence=["#3498DB"],
    )
    fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, use_container_width=True)
