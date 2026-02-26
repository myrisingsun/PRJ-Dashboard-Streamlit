"""
Reusable finance table with plan/fact colour coding.
"""
import pandas as pd


MONTH_NAMES = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
               "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]


def highlight_plan_fact(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    """
    Apply background colour to fact columns:
      - Green  if fact <= plan
      - Red    if fact >  plan
    """
    def _style(row):
        styles = [""] * len(row)
        for month in MONTH_NAMES:
            plan_col = f"{month}_план"
            fact_col = f"{month}_факт"
            if plan_col in row.index and fact_col in row.index:
                pi = row.index.get_loc(fact_col)
                plan_val = pd.to_numeric(row[plan_col], errors="coerce") or 0
                fact_val = pd.to_numeric(row[fact_col], errors="coerce") or 0
                if fact_val > 0:
                    color = "#d4efdf" if fact_val <= plan_val else "#fadbd8"
                    styles[pi] = f"background-color: {color}"
        return styles

    return df.style.apply(_style, axis=1)


def format_money(v) -> str:
    """Format a numeric value as '1 234 567'."""
    try:
        return f"{int(v):,}".replace(",", " ") if pd.notna(v) and v != 0 else ""
    except (ValueError, TypeError):
        return ""
