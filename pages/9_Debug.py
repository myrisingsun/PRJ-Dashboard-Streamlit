"""
Diagnostic page — inspect raw Google Sheet rows with column indices.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Debug", page_icon="🔍", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import _load_raw

authenticator = require_auth()
render_sidebar_user(authenticator)

st.title("🔍 Диагностика сырых данных")

sheet = st.selectbox("Лист", [
    "05.PRJ_MONEY_2026",
    "01.PRJ_LIST",
    "04.PRJ_TEAM",
])

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
