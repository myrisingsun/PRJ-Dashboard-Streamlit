"""
Page 4 — Project teams and bonus distribution calculator
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Team", page_icon="👥", layout="wide")

from auth import render_sidebar_user, require_auth
from data.loader import load_prj_team, _find_col

authenticator = require_auth()
render_sidebar_user(authenticator)

st.title("👥 Команды и распределение премий")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Цветные бейджи ролей */
.role-badge { display:inline-block; font-size:0.72em; font-weight:700;
              padding:2px 9px; border-radius:20px; color:#fff; }
.role-A  { background:#E74C3C; }
.role-BA { background:#3498DB; }
.role-S  { background:#2ECC71; }

/* Контейнер матрицы */
.team-wrap { width:100%; overflow-x:auto; margin-bottom:20px;
             border:1px solid #e0e4e8; border-radius:8px; }

/* Таблица */
.team-table { border-collapse:collapse; font-size:0.80em; background:#fff; }
.team-table thead th { background:#2C3E50; color:#ECF0F1; font-weight:700;
                       padding:4px 3px; text-align:center; border:1px solid #1A252F; }
/* Заголовок первой колонки (Проект) */
.team-table thead th.th-prj { text-align:left; padding:6px 8px;
                               white-space:nowrap; min-width:140px; }
/* Заголовки сотрудников — вертикальный текст */
.team-table thead th.th-emp {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    transform: rotate(180deg);
    height: 90px;
    width: 30px;
    min-width: 30px;
    max-width: 30px;
    padding: 6px 4px;
    vertical-align: bottom;
    white-space: nowrap;
    font-size: 0.78em;
}
.team-table td { padding:4px 3px; border:1px solid #E8E8E8;
                 text-align:center; width:30px; min-width:30px; }
/* Колонка проекта */
.team-table td.td-code { text-align:left; font-size:0.78em; font-weight:700;
                         color:#95a5a6; text-transform:uppercase;
                         max-width:180px; min-width:140px;
                         padding:4px 8px; }
.team-table td.td-code a { color:#2980b9; text-decoration:none; }
.team-table td.td-code a:hover { text-decoration:underline; }
.team-table tr:nth-child(even) td { background:#F8FAFB; }
.team-table tr:hover td { background:#EBF5FB; }

/* Итоговая строка */
.team-table tr.summary-row td { background:#2C3E50 !important;
                                 color:#ECF0F1 !important; font-weight:700;
                                 border:1px solid #1A252F; }
.team-table tr.summary-row td:first-child { text-align:left; }

/* Название проекта под кодом — обрезать длинные */
.td-name { font-size:0.80em; color:#7f8c8d; font-weight:400;
           text-transform:none; margin-top:2px;
           white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
           max-width:160px; }

/* Карточка команды проекта */
.prj-team-wrap { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.prj-member-card { display:flex; align-items:center; gap:6px;
                   background:#F8FAFB; border:1px solid #E8E8E8;
                   border-radius:6px; padding:5px 10px; font-size:0.85em; }
.prj-member-name { font-weight:600; color:#2C3E50; }
</style>
""", unsafe_allow_html=True)

# ── Load ─────────────────────────────────────────────────────────────────────
with st.spinner("Загрузка данных..."):
    team = load_prj_team()

if team.empty:
    st.error("Не удалось загрузить данные из листа 04.PRJ_TEAM.")
    st.stop()

code_col = _find_col(team, ["Код проекта", "Код"])
name_col = _find_col(team, ["Название"])
emp_cols = [c for c in team.columns if c not in {code_col, name_col} and c]

ROLE_COLORS = {"A": "#E74C3C", "БА": "#3498DB", "S": "#2ECC71"}
VALID_ROLES = {"A", "S", "БА"}

# ── KPI computation ───────────────────────────────────────────────────────────
emp_project_counts: dict = {}   # переиспользуется в матрице и графике
total_employees = 0
total_rp = 0

for emp in emp_cols:
    col_data = team[emp].fillna("").astype(str).str.strip()
    active = col_data[col_data.isin(VALID_ROLES)]
    if not active.empty:
        total_employees += 1
        emp_project_counts[emp] = len(active)
        if "A" in active.values:
            total_rp += 1

avg_workload = round(sum(emp_project_counts.values()) / total_employees, 1) \
               if total_employees else 0.0
total_projects = len(team)

# ── KPI render ────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Сотрудников в командах", total_employees)
k2.metric("Проектов", total_projects)
k3.metric("Руководителей (РП)", total_rp)
k4.metric("Среднее проектов / чел.", avg_workload)

st.divider()

# ── HTML-матрица участия ──────────────────────────────────────────────────────
st.subheader("Матрица участия")


def build_role_badge(role_val: str) -> str:
    v = str(role_val).strip()
    if v == "A":
        return '<span class="role-badge role-A">A</span>'
    if v == "БА":
        return '<span class="role-badge role-BA">БА</span>'
    if v == "S":
        return '<span class="role-badge role-S">S</span>'
    return ""


def build_team_matrix(df: pd.DataFrame, code_col: str, emp_cols: list) -> str:
    # Header
    header_cells = '<th class="th-prj">Проект</th>' + "".join(
        f'<th class="th-emp">{emp}</th>' for emp in emp_cols
    )
    # Body rows
    body_rows = []
    for _, row in df.iterrows():
        code_val = str(row.get(code_col, "")).strip() if code_col else ""
        name_val = str(row.get(name_col, "")).strip() if name_col else ""
        name_part = f'<div class="td-name">{name_val}</div>' if name_val else ""
        code_td = (
            f'<td class="td-code"><a href="/Project?project={code_val}">{code_val}</a>{name_part}</td>'
            if code_val else '<td class="td-code"></td>'
        )
        role_cells = "".join(
            f"<td>{build_role_badge(row.get(emp, ''))}</td>" for emp in emp_cols
        )
        body_rows.append(f"<tr>{code_td}{role_cells}</tr>")

    # Summary row
    summary_cells = "".join(
        f"<td>{emp_project_counts.get(emp, '') or ''}</td>"
        if emp_project_counts.get(emp, 0) > 0
        else "<td></td>"
        for emp in emp_cols
    )
    summary_row = (
        f'<tr class="summary-row"><td>Итого проектов</td>{summary_cells}</tr>'
    )

    return (
        '<div class="team-wrap">'
        '<table class="team-table">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}{summary_row}</tbody>"
        "</table></div>"
    )


st.markdown(build_team_matrix(team, code_col, emp_cols), unsafe_allow_html=True)
st.caption("**A** — руководитель проекта  |  **БА** — бизнес-аналитик  |  **S** — участник")

st.divider()

# ── Команда проекта ───────────────────────────────────────────────────────────
st.subheader("Команда проекта")

# Build project option list: "CODE — Name" or just "CODE"
prj_options = []
for _, row in team.iterrows():
    code_v = str(row.get(code_col, "")).strip() if code_col else ""
    name_v = str(row.get(name_col, "")).strip() if name_col else ""
    if code_v:
        prj_options.append((f"{code_v} — {name_v}" if name_v else code_v, code_v))

if prj_options:
    sel_prj_label = st.selectbox(
        "Выбрать проект",
        [lbl for lbl, _ in prj_options],
        key="team_sel_project",
    )
    sel_prj_code = next((c for lbl, c in prj_options if lbl == sel_prj_label), None)

    if sel_prj_code and code_col:
        prj_rows = team[team[code_col] == sel_prj_code]
        if not prj_rows.empty:
            prj_row = prj_rows.iloc[0]
            role_order = {"A": 0, "БА": 1, "S": 2}
            members = sorted(
                [(emp, str(prj_row.get(emp, "")).strip())
                 for emp in emp_cols
                 if str(prj_row.get(emp, "")).strip() in VALID_ROLES],
                key=lambda x: role_order.get(x[1], 99),
            )

            if members:
                # Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Всего в команде", len(members))
                m2.metric("Руководителей (A)", sum(1 for _, r in members if r == "A"))
                m3.metric("Бизнес-аналитиков (БА)", sum(1 for _, r in members if r == "БА"))
                m4.metric("Участников (S)", sum(1 for _, r in members if r == "S"))

                # Member cards
                cards_html = '<div class="prj-team-wrap">'
                for emp, role in members:
                    badge = build_role_badge(role)
                    cards_html += (
                        f'<div class="prj-member-card">'
                        f'{badge} <span class="prj-member-name">{emp}</span>'
                        f'</div>'
                    )
                cards_html += "</div>"
                st.markdown(cards_html, unsafe_allow_html=True)
            else:
                st.info("Нет данных о команде для этого проекта.")

st.divider()

# ── Профиль сотрудника ────────────────────────────────────────────────────────
st.subheader("Сводка по сотруднику")

selected_emp = st.selectbox("Выбрать сотрудника", emp_cols)

if selected_emp:
    emp_data = team[team[selected_emp].fillna("").astype(str).str.strip().isin(["A", "S", "БА"])].copy()

    if emp_data.empty:
        st.info(f"{selected_emp} не участвует ни в одном проекте.")
    else:
        display_cols = [c for c in [code_col, name_col, selected_emp] if c]
        emp_display = emp_data[display_cols].rename(columns={selected_emp: "Роль"})
        st.dataframe(emp_display, use_container_width=True, hide_index=True)
        st.metric("Количество проектов", len(emp_data))

st.divider()

# ── График нагрузки (stacked bar) ─────────────────────────────────────────────
st.subheader("Нагрузка по сотрудникам (по ролям)")

workload_rows = []
for emp in emp_cols:
    if emp not in emp_project_counts:
        continue
    col_data = team[emp].fillna("").astype(str).str.strip()
    count_a  = int((col_data == "A").sum())
    count_ba = int((col_data == "БА").sum())
    count_s  = int((col_data == "S").sum())
    workload_rows.append({
        "Сотрудник": emp,
        "A":   count_a,
        "БА":  count_ba,
        "S":   count_s,
        "Всего": count_a + count_ba + count_s,
    })

if workload_rows:
    wl_df = pd.DataFrame(workload_rows).sort_values("Всего", ascending=True)

    fig_wl = go.Figure()
    for role, color, label in [
        ("S",  "#2ECC71", "S — участник"),
        ("БА", "#3498DB", "БА — бизнес-аналитик"),
        ("A",  "#E74C3C", "A — руководитель"),
    ]:
        vals = wl_df[role]
        fig_wl.add_trace(go.Bar(
            name=label,
            y=wl_df["Сотрудник"],
            x=vals,
            orientation="h",
            marker_color=color,
            text=[str(v) if v > 0 else "" for v in vals],
            textposition="inside",
            insidetextanchor="middle",
        ))

    fig_wl.update_layout(
        barmode="stack",
        height=max(280, len(wl_df) * 38 + 80),
        xaxis_title="Количество проектов",
        yaxis_title="",
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_wl.update_xaxes(dtick=1, gridcolor="#E8E8E8", showgrid=True)
    st.plotly_chart(fig_wl, use_container_width=True)

st.divider()

# ── Калькулятор премий ────────────────────────────────────────────────────────
st.subheader("Распределение премии")

bonus_pool = st.number_input(
    "Общий фонд премии (₽)",
    min_value=0,
    value=1_000_000,
    step=10_000,
    format="%d",
)

method = st.radio(
    "Метод распределения",
    options=["Поровну по участникам", "С весом по роли (A=3x, БА=2x, S=1x)", "С весом по количеству проектов"],
)

ROLE_WEIGHTS = {"A": 3, "БА": 2, "S": 1}


def fmt_bonus_label(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} млн"
    if v >= 1_000:
        return f"{v / 1_000:.1f} тыс"
    return f"{v:.0f} ₽"


if st.button("Рассчитать"):
    # Build participation table: employee → list of roles
    rows = []
    for emp in emp_cols:
        col_data = team[emp].fillna("").astype(str).str.strip()
        roles = col_data[col_data.isin(["A", "S", "БА"])].tolist()
        if roles:
            rows.append({
                "Сотрудник": emp,
                "Количество проектов": len(roles),
                "Роли": ", ".join(roles),
                "Макс. роль": "A" if "A" in roles else ("БА" if "БА" in roles else "S"),
            })

    if not rows:
        st.warning("Нет данных об участии сотрудников.")
    else:
        result_df = pd.DataFrame(rows)

        if method == "Поровну по участникам":
            per_person = bonus_pool / len(result_df)
            result_df["Премия (₽)"] = per_person

        elif "роли" in method:
            result_df["Вес"] = result_df["Макс. роль"].map(ROLE_WEIGHTS).fillna(1)
            total_weight = result_df["Вес"].sum()
            result_df["Премия (₽)"] = result_df["Вес"] / total_weight * bonus_pool

        else:  # by project count
            total_proj = result_df["Количество проектов"].sum()
            result_df["Премия (₽)"] = result_df["Количество проектов"] / total_proj * bonus_pool

        result_df["Премия (₽)"] = result_df["Премия (₽)"].round(2)

        show_cols = ["Сотрудник", "Количество проектов", "Роли", "Премия (₽)"]
        st.dataframe(result_df[show_cols], use_container_width=True, hide_index=True)

        # Total check
        st.metric("Итого распределено", f"{result_df['Премия (₽)'].sum():,.2f} ₽")

        # Download
        csv = result_df[show_cols].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="Скачать CSV",
            data=csv,
            file_name="bonus_distribution.csv",
            mime="text/csv",
        )

        # Viz — go.Bar with text labels
        sorted_df = result_df.sort_values("Премия (₽)", ascending=True)
        bar_colors = sorted_df["Макс. роль"].map(ROLE_COLORS).fillna("#95A5A6").tolist()

        fig = go.Figure(go.Bar(
            y=sorted_df["Сотрудник"],
            x=sorted_df["Премия (₽)"],
            orientation="h",
            marker_color=bar_colors,
            text=sorted_df["Премия (₽)"].apply(fmt_bonus_label),
            textposition="outside",
            cliponaxis=False,
        ))
        fig.update_layout(
            height=max(300, len(sorted_df) * 35 + 80),
            margin=dict(l=0, r=130, t=10, b=0),
            plot_bgcolor="#ffffff",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_title="₽",
            yaxis_title="",
            showlegend=False,
        )
        fig.update_xaxes(gridcolor="#E8E8E8", showgrid=True)
        st.plotly_chart(fig, use_container_width=True)
