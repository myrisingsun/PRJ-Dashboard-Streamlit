"""
Reusable status badge / indicator helpers.
"""
from data.loader import STATUS_COLORS, STATUS_EMOJI


def status_emoji(status: str) -> str:
    return STATUS_EMOJI.get(status, "⚪")


def status_html_badge(status: str) -> str:
    """Return an HTML span with coloured background for use in st.markdown(unsafe_allow_html=True)."""
    color = STATUS_COLORS.get(status, "#BDC3C7")
    emoji = STATUS_EMOJI.get(status, "⚪")
    return (
        f'<span style="background-color:{color};color:white;'
        f'padding:2px 8px;border-radius:4px;font-size:0.85em;">'
        f'{emoji} {status}</span>'
    )
