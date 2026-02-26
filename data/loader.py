"""
Google Sheets data loader with caching.
Supports both Streamlit secrets (secrets.toml) and environment variables (Docker).
"""
import json
import os
import re
from typing import Optional

import gspread
import pandas as pd
import streamlit as st

STATUS_COLORS = {
    "По плану":      "#2ECC71",
    "Есть риски":    "#E74C3C",
    "Приостановлен": "#95A5A6",
    "Отстает":       "#F1C40F",
}

STATUS_EMOJI = {
    "По плану":      "🟢",
    "Есть риски":    "🔴",
    "Приостановлен": "⚫",
    "Отстает":       "🟡",
}


def _get_creds_info() -> dict:
    """Return service account credentials dict from secrets or env var."""
    try:
        return dict(st.secrets["gcp_service_account"])
    except Exception:
        return json.loads(os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "{}"))


def _get_sheet_id() -> str:
    """Load Google Sheet ID from Streamlit secrets or environment variable."""
    try:
        return st.secrets["GOOGLE_SHEET_ID"]
    except Exception:
        return os.environ.get("GOOGLE_SHEET_ID", "")


@st.cache_data(ttl=300)
def _load_raw(sheet_name: str) -> list[list[str]]:
    """Fetch raw cell values from a worksheet (cached 5 min)."""
    # gspread 6.x — service_account_from_dict is the correct approach
    gc = gspread.service_account_from_dict(_get_creds_info())
    sh = gc.open_by_key(_get_sheet_id())
    ws = sh.worksheet(sheet_name)
    return ws.get_all_values()


# ---------------------------------------------------------------------------
# Sheet parsers
# ---------------------------------------------------------------------------

def _strip_df(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from all string cells."""
    return df.map(lambda x: x.strip() if isinstance(x, str) else x)


def _non_empty_rows(data: list[list[str]], start: int) -> list[list[str]]:
    """Return rows from `start` that have at least one non-empty cell in column 0."""
    return [r for r in data[start:] if r and r[0].strip()]


_MONTH_MAP_RU = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4,
    "май": 5, "июн": 6, "июл": 7, "авг": 8,
    "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
}


def _parse_month_label(label: str) -> Optional[pd.Timestamp]:
    """Convert a column label like '2026_Янв' → pd.Timestamp('2026-01-01').

    Returns None if the label cannot be parsed.
    """
    if not label or label.startswith("col_"):
        return None
    parts = label.split("_", 1)
    if len(parts) != 2:
        return None
    year_str, month_str = parts
    try:
        year = int(year_str)
    except ValueError:
        return None
    month_num = _MONTH_MAP_RU.get(month_str.lower())
    if month_num is None:
        return None
    return pd.Timestamp(year=year, month=month_num, day=1)


@st.cache_data(ttl=300)
def load_prj_list() -> pd.DataFrame:
    """
    Sheet 01.PRJ_LIST
    Row 0-1: metadata / merge rows (skip)
    Row 2: column headers
    Row 3+: project data
    """
    data = _load_raw("01.PRJ_LIST")
    if len(data) < 4:
        return pd.DataFrame()

    header = [h.strip() for h in data[2]]
    rows = _non_empty_rows(data, 3)

    # Pad short rows to match header length
    max_len = len(header)
    rows = [r + [""] * (max_len - len(r)) for r in rows]

    df = pd.DataFrame(rows, columns=header)
    df = _strip_df(df)
    return df


@st.cache_data(ttl=300)
def load_oper_list() -> pd.DataFrame:
    """
    Sheet 02.OPER_LIST – same layout as 01.PRJ_LIST
    """
    data = _load_raw("02.OPER_LIST")
    if len(data) < 4:
        return pd.DataFrame()

    header = [h.strip() for h in data[2]]
    rows = _non_empty_rows(data, 3)
    max_len = len(header)
    rows = [r + [""] * (max_len - len(r)) for r in rows]

    df = pd.DataFrame(rows, columns=header)
    df = _strip_df(df)
    return df


@st.cache_data(ttl=300)
def load_prj_status() -> pd.DataFrame:
    """
    Sheet 03.PRJ_STATUS
    Rows 0-2: multi-level header (year / quarter / month).
    Row 3+: data rows, two rows per key work per project (Plan / Fact).

    Columns layout (0-indexed):
      0  – №  (row number, may be empty for Fact rows)
      1  – Код проекта  (forward-filled from Plan row)
      2  – Название работы  (each row has its own value — NOT forward-filled)
      3  – col3  (reserved)
      4  – Тип  ('План' or 'Факт')
      5  – Доп. описание  (clarified name / sub-description)
      6  – Срок  (e.g. "Q1 2025 - Q4 2026")
      7+ – monthly milestone flags ('1' = executed, 'X' = key milestone)
    """
    data = _load_raw("03.PRJ_STATUS")
    if len(data) < 5:
        return pd.DataFrame()

    # Sheet structure: row 0 = year, row 1 = quarter (unused), row 2 = month
    year_row  = data[0]
    month_row = data[2]

    # Fixed columns before monthly data
    fixed_cols = ["№", "Код проекта", "Название работы", "col3", "Тип", "Доп. описание", "Срок"]
    n_fixed = len(fixed_cols)

    # Build month column labels.
    # Year cells are merged in the sheet, so gspread returns the value only in the
    # first cell of each year group — all others are empty. Forward-fill current_year
    # so every monthly column gets a proper "YYYY_Месяц" label.
    # Columns with an empty month cell are visual separators — skip them entirely.
    month_cols = []
    current_year = ""
    for i in range(n_fixed, max(len(year_row), len(month_row))):
        y = year_row[i].strip() if i < len(year_row) else ""
        if y:
            current_year = y
        month = month_row[i].strip() if i < len(month_row) else ""
        if not month:
            continue  # separator column — skip
        label = f"{current_year}_{month}" if current_year else f"col_{i}"
        month_cols.append(label)

    all_cols = fixed_cols + month_cols

    rows = []
    for row in data[3:]:
        # Skip completely empty rows (e.g. spacer rows between projects)
        if not row or not any(c.strip() for c in row):
            continue
        padded = row + [""] * (len(all_cols) - len(row))
        rows.append(padded[: len(all_cols)])

    df = pd.DataFrame(rows, columns=all_cols)
    df = _strip_df(df)

    # Forward-fill Код проекта only (merged cells appear only in Plan row)
    # "Название работы" (col 2) is NOT forward-filled — each row has its own value
    df["Код проекта"] = df["Код проекта"].replace("", None).ffill()

    # Drop rows where Код проекта is still empty (truly empty header/spacer rows)
    df = df[df["Код проекта"].notna() & (df["Код проекта"] != "")]

    return df


def _clean_col_name(raw: str, idx: int) -> str:
    """
    Sanitize a column name coming from a Google Sheet cell:
    - replace non-breaking spaces and tabs
    - take only the first non-empty line (cells often have multi-line content)
    - fall back to positional name if the result is empty or looks like a legend
    """
    s = raw.replace("\xa0", " ").replace("\t", " ").strip()
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    if not lines:
        return f"_col_{idx}"
    first = lines[0]
    # Legend cells look like "A - описание..." — skip them
    if first.startswith(("A -", "S -", "БА -", "A–", "S–", "БА–")):
        return f"_legend_{idx}"
    return first


def _dedup_names(names: list[str]) -> list[str]:
    """Add _2, _3 … suffixes to duplicate column names."""
    seen: dict[str, int] = {}
    result = []
    for name in names:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 1
            result.append(name)
    return result


@st.cache_data(ttl=300)
def load_prj_team() -> pd.DataFrame:
    """
    Sheet 04.PRJ_TEAM
    Row 0: empty
    Row 1: legend / multi-line descriptions (skip for names)
    Row 2: actual header — col 0: '#', col 1: 'Код проекта', col 2: 'Проект',
           col 3+: employee names (abbreviated: 'Пахарев К.А.')
    Row 3+: project data rows, values are 'A' / 'S' / 'БА' or empty
    """
    data = _load_raw("04.PRJ_TEAM")
    if len(data) < 4:
        return pd.DataFrame()

    name_row = data[2]   # row 2 has clean abbreviated names
    n_fixed  = 3         # skip '#', 'Код проекта', 'Проект'

    raw_names = [
        _clean_col_name(name_row[i], i)
        for i in range(n_fixed, len(name_row))
        if i < len(name_row)
    ]
    clean_names = _dedup_names(raw_names)

    header = ["Код проекта", "Название"] + clean_names
    rows = _non_empty_rows(data, 3)           # data starts at row 3
    max_len = len(header)
    rows = [(r + [""] * (max_len - len(r)))[:max_len] for r in rows]

    df = pd.DataFrame(rows, columns=header)
    df = _strip_df(df)

    emp_cols = [c for c in clean_names if not c.startswith(("_legend_", "_col_"))]
    keep = ["Код проекта", "Название"] + emp_cols
    keep = [c for c in keep if c in df.columns]
    return df[keep]


def get_pm_per_project() -> dict[str, str]:
    """
    Returns {project_code: 'PM Name, PM2 Name'} from PRJ_TEAM.
    РП = employee with role 'A' in a project row.
    """
    data = _load_raw("04.PRJ_TEAM")
    if len(data) < 4:
        return {}

    name_row = data[2]
    n_fixed  = 3
    employees = [
        (i, name_row[i].strip())
        for i in range(n_fixed, len(name_row))
        if i < len(name_row) and name_row[i].strip()
    ]

    result: dict[str, str] = {}
    for row in data[3:]:
        if not row or not (len(row) > 1 and row[1].strip()):
            continue
        code = row[1].strip()
        pms = [
            name for idx, name in employees
            if idx < len(row) and row[idx].strip().upper() == "A"
        ]
        if pms:
            result[code] = ", ".join(pms)
    return result


def _parse_rub(s: str) -> float:
    """Parse a Russian money string like '1 900 000 ₽' → 1900000.0"""
    clean = re.sub(r"[₽\s\xa0]", "", str(s)).replace(",", ".")
    try:
        return float(clean) if clean else 0.0
    except ValueError:
        return 0.0


_PRJ_CODE_RE = re.compile(r"^[A-Z]{2,6}\.\d{4}$")


def get_finance_per_project() -> pd.DataFrame:
    """
    Returns per-project finance totals from '05.PRJ_MONEY_2026'.

    Rule: only rows where column A (col 0) contains a project code
    (pattern: 2-6 uppercase letters, dot, 4 digits — e.g. ADMN.0001).
    'Итого' rows for the same code are used as per-project summaries;
    individual position rows for the same code are skipped to avoid
    double-counting.

    Column layout (0-indexed):
      0  – project code
      1  – row label (used to detect 'Итого' rows)
      5  – Бюджет 2026
      32 – План оплат
      33 – Факт оплат
      34 – Отклонение
      35 – Запланировано, но не оплачено
    """
    data = _load_raw("05.PRJ_MONEY_2026")
    rows: list[dict] = []

    for row in data:
        if len(row) < 6:
            continue
        c0 = row[0].strip()
        if not c0 or not _PRJ_CODE_RE.match(c0):
            continue   # only rows with a project code in col A

        c1 = row[1].strip() if len(row) > 1 else ""
        if "итого" not in c1.lower():
            continue   # skip individual position rows; use only summary rows

        rows.append({
            "Код":         c0,
            "Бюджет":      _parse_rub(row[5]  if len(row) > 5  else ""),
            "План_оплат":  _parse_rub(row[32] if len(row) > 32 else ""),
            "Факт_оплат":  _parse_rub(row[33] if len(row) > 33 else ""),
            "Отклонение":  _parse_rub(row[34] if len(row) > 34 else ""),
            "Не_оплачено": _parse_rub(row[35] if len(row) > 35 else ""),
        })

    if not rows:
        return pd.DataFrame(columns=["Код", "Бюджет", "План_оплат", "Факт_оплат",
                                     "Отклонение", "Не_оплачено"])
    df = pd.DataFrame(rows)
    return df.groupby("Код")[["Бюджет", "План_оплат", "Факт_оплат",
                               "Отклонение", "Не_оплачено"]].sum().reset_index()


@st.cache_data(ttl=300)
def load_prj_money() -> pd.DataFrame:
    """
    Sheet 05.PRJ_MONEY_2026
    Complex structure: rows grouped by IT product.
    Header layout (rows 0-2 are multi-level):
      Col 0: IT-product / position name
      Col 1: Бюджет 2026
      Col 2-25: Plan / Fact for Jan–Dec (12 months × 2 = 24)
      Col 26-29: Итог plan, Итог fact, Отклонение, Не оплачено
    Data rows: product header, position rows, Итого row per group.
    """
    data = _load_raw("05.PRJ_MONEY_2026")
    if len(data) < 5:
        return pd.DataFrame()

    # Build column names from rows 0-2
    month_names = [
        "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
        "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
    ]
    fixed = ["Позиция", "Бюджет_2026"]
    month_cols = []
    for m in month_names:
        month_cols += [f"{m}_план", f"{m}_факт"]
    summary = ["План_оплат", "Факт_оплат", "Отклонение", "Не_оплачено"]
    all_cols = fixed + month_cols + summary

    rows = []
    current_product = ""
    for row in data[3:]:
        if not row or not any(c.strip() for c in row):
            continue
        padded = row + [""] * (len(all_cols) - len(row))
        padded = padded[: len(all_cols)]

        pos_name = padded[0].strip()
        if not pos_name:
            continue

        # Detect product header: no numeric data and not "Итого"
        # Heuristic: budget cell is empty → it's a product header row
        if not padded[1].strip() and "итого" not in pos_name.lower():
            current_product = pos_name
            continue

        record = {"IT_продукт": current_product, **dict(zip(all_cols, padded))}
        rows.append(record)

    df = pd.DataFrame(rows)
    df = _strip_df(df)

    # Convert numeric-looking columns
    numeric_cols = [c for c in df.columns if c not in ("IT_продукт", "Позиция")]
    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col].str.replace(" ", "").str.replace(",", ".").str.replace("\xa0", ""),
            errors="coerce",
        )
    return df


# ---------------------------------------------------------------------------
# Derived / aggregated helpers
# ---------------------------------------------------------------------------

def get_prj_summary() -> pd.DataFrame:
    """
    Merge PRJ_LIST + PRJ_MONEY for the Index page KPI table.
    Returns one row per project with budget/fact/remaining columns.
    """
    prj = load_prj_list()
    if prj.empty:
        return pd.DataFrame()

    money = load_prj_money()

    # Try to find the canonical column names (they may vary by actual sheet)
    code_col    = _find_col(prj, ["Код проекта", "Код", "CODE"])
    name_col    = _find_col(prj, ["Сокращенное название проекта", "Название", "Сокращённое название"])
    status_col  = _find_col(prj, ["Текущий статус", "Статус"])
    period_col  = _find_col(prj, ["Плановый срок", "Срок"])
    bitrix_col  = _find_col(prj, ["Ссылка на приказ в Bitrix24 (PDF)", "Bitrix24", "Bitrix"])
    prod_col    = _find_col(prj, ["Ссылка на систему PROD", "PROD", "Prod"])

    result = prj[[c for c in [code_col, name_col, status_col, period_col, bitrix_col, prod_col] if c]].copy()
    result.columns = [
        c for c in ["Код", "Название", "Статус", "Срок", "Bitrix", "PROD"]
        if True  # keep same length
    ][: len(result.columns)]

    if not money.empty and "Факт_оплат" in money.columns and "Бюджет_2026" in money.columns:
        fin = money.groupby("IT_продукт")[["Бюджет_2026", "Факт_оплат"]].sum().reset_index()
        fin.columns = ["Код", "Бюджет", "Факт"]
        result = result.merge(fin, on="Код", how="left")
        result["Осталось"] = result["Бюджет"] - result["Факт"]

    return result


def _find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return the first candidate column name that exists in df."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def parse_date_range(text: str):
    """
    Parse a date range string like 'Q1 2024 - Q2 2026' or 'янв 2025 - дек 2026'.
    Returns (start_date, end_date) as pd.Timestamp or None.
    """
    if not text or not isinstance(text, str):
        return None, None

    quarter_map = {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}
    month_map = {
        "янв": "01", "фев": "02", "мар": "03", "апр": "04",
        "май": "05", "июн": "06", "июл": "07", "авг": "08",
        "сен": "09", "окт": "10", "ноя": "11", "дек": "12",
    }

    def parse_single(s: str):
        s = s.strip()
        # Match "Q1 2025"
        m = re.match(r"(Q[1-4])\s*(\d{4})", s, re.IGNORECASE)
        if m:
            month = quarter_map[m.group(1).upper()]
            return pd.Timestamp(f"{m.group(2)}-{month}-01")
        # Match "янв 2025"
        for ru, num in month_map.items():
            if ru in s.lower():
                year_m = re.search(r"(\d{4})", s)
                if year_m:
                    return pd.Timestamp(f"{year_m.group(1)}-{num}-01")
        # Match plain "2025"
        m = re.match(r"(\d{4})", s)
        if m:
            return pd.Timestamp(f"{m.group(1)}-01-01")
        return None

    parts = re.split(r"\s*[-–]\s*", text, maxsplit=1)
    start = parse_single(parts[0]) if len(parts) > 0 else None
    end   = parse_single(parts[1]) if len(parts) > 1 else None
    return start, end
