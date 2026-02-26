"""
Authentication helpers using streamlit-authenticator.
Call require_auth() at the top of every page.
"""
from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import yaml


def _load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_authenticator() -> stauth.Authenticate:
    config = _load_config()
    return stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )


def require_auth() -> stauth.Authenticate:
    """
    Verify authentication on every page.
    - If the user has a valid cookie: authenticates silently, returns authenticator.
    - If not authenticated: shows login form and stops rendering.
    """
    authenticator = get_authenticator()

    # login() checks cookie first; only shows form if not yet authenticated
    authenticator.login(location="main")

    status = st.session_state.get("authentication_status")

    if status is False:
        st.error("Неверный логин или пароль")
        st.stop()
    elif status is None:
        st.info("Введите логин и пароль для входа")
        st.stop()

    # status is True — authenticated
    return authenticator


def render_sidebar_user(authenticator: stauth.Authenticate) -> None:
    """Render user info and logout button in the sidebar."""
    name = st.session_state.get("name", "")
    st.sidebar.markdown(f"**👤 {name}**")
    authenticator.logout("Выйти", location="sidebar")
    st.sidebar.divider()
    if st.sidebar.button("🔄 Обновить данные", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
