"""
Reusable Plotly Gantt chart builder.
"""
import pandas as pd
import plotly.express as px

from data.loader import STATUS_COLORS


def build_gantt(
    df: pd.DataFrame,
    x_start: str = "Начало",
    x_end: str = "Конец",
    y: str = "Проект",
    color: str = "Статус",
    height_per_row: int = 40,
    min_height: int = 300,
) -> "plotly.graph_objects.Figure":
    """
    Build a Plotly timeline (Gantt) figure.

    Parameters
    ----------
    df : DataFrame with x_start, x_end, y, color columns
    """
    df = df.dropna(subset=[x_start, x_end])
    df = df[df[x_start] < df[x_end]]

    if df.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(text="Нет данных для Ганта", showarrow=False, font=dict(size=14))
        return fig

    fig = px.timeline(
        df,
        x_start=x_start,
        x_end=x_end,
        y=y,
        color=color,
        color_discrete_map=STATUS_COLORS,
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=max(min_height, len(df) * height_per_row + 100),
        xaxis_title="",
        yaxis_title="",
        legend_title="Статус",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig
