"""Shared Streamlit UI components for all agent architectures."""

import os
from typing import Optional

import streamlit as st

from utils.session_manager import SessionManager


def mask_key(key: str) -> str:
    """Mask API key for display."""
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


def render_sidebar_settings(
    session_manager: SessionManager,
    default_model: str = "gpt-4o-mini",
    default_base_url: str = "https://api.openai.com",
) -> tuple[str, str, str]:
    """
    Render sidebar with settings.
    
    Returns:
        Tuple of (api_key, model, base_url)
    """
    st.sidebar.header("Session Management")
    existing_sessions = session_manager.list_sessions()
    if existing_sessions:
        selected_session = st.sidebar.selectbox(
            "Load existing session",
            ["-- New Session --"] + existing_sessions,
            key="session_selector",
        )
        if selected_session != "-- New Session --":
            if st.sidebar.button("Load Session"):
                session = session_manager.load_session(selected_session)
                if session:
                    st.session_state.session_id = session.session_id
                    st.rerun()

    if st.sidebar.button("New Session"):
        new_session = session_manager.create_session()
        st.session_state.session_id = new_session.session_id
        st.rerun()

    if st.session_state.get("session_id"):
        if st.sidebar.button("Delete Current Session"):
            session_manager.delete_session(st.session_state.session_id)
            st.session_state.session_id = None
            st.rerun()

    st.sidebar.divider()

    st.sidebar.header("OpenAI Settings")
    env_key = os.getenv("OPENAI_API_KEY")
    st.sidebar.write(f"API key (.env OPENAI_API_KEY): {mask_key(env_key) if env_key else '(not set)'}")

    api_key = st.sidebar.text_input(
        "API key override (optional)",
        type="password",
        value="",
        help="Leave blank to use OPENAI_API_KEY from the .env file.",
    )
    model = st.sidebar.text_input("Model", value=default_model)
    base_url = st.sidebar.text_input("Base URL", value=default_base_url)

    return api_key.strip() or env_key or "", model, base_url


def render_file_upload() -> tuple[list, list]:
    """Render file and image upload widgets."""
    st.sidebar.divider()
    st.sidebar.header("File Upload")
    uploaded_files = st.sidebar.file_uploader(
        "Upload files",
        type=["txt", "pdf", "csv", "json", "md", "py", "log"],
        accept_multiple_files=True,
    )

    st.sidebar.divider()
    st.sidebar.header("Image Upload")
    uploaded_images = st.sidebar.file_uploader(
        "Upload images",
        type=["png", "jpg", "jpeg", "gif", "webp"],
        accept_multiple_files=True,
        key="image_uploader",
    )

    return uploaded_files or [], uploaded_images or []


def render_db_connection_ui(session_manager: SessionManager) -> None:
    """Render database connection UI."""
    st.sidebar.divider()
    st.sidebar.header("Database Connection")
    db_type = st.sidebar.selectbox("Database Type", ["postgresql", "mysql", "sqlite"])
    db_connection_string = st.sidebar.text_input(
        "Connection String",
        type="password",
        help="e.g., postgresql://user:pass@host:port/dbname",
    )
    # DB connection logic would go here (similar to app.py)
