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


def get_current_role() -> str:
    """Return the role of the currently authenticated user ('admin' or 'viewer')."""
    config = _load_config()
    username = st.session_state.get("username", "")
    return config.get("roles", {}).get(username, "viewer")


def require_role(allowed_roles: list[str]) -> None:
    """Stop page rendering if the current user's role is not in allowed_roles."""
    role = get_current_role()
    if role not in allowed_roles:
        st.error("🚫 Нет доступа к этому разделу.")
        st.stop()


def render_sidebar_user(authenticator: stauth.Authenticate) -> None:
    """Render user info and logout button in the sidebar."""
    name = st.session_state.get("name", "")
    role = get_current_role()
    role_label = " *(просмотр)*" if role == "viewer" else ""
    st.sidebar.markdown(f"**👤 {name}**{role_label}")
    authenticator.logout("Выйти", location="sidebar")
    st.sidebar.divider()
    if st.sidebar.button("🔄 Обновить данные", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
