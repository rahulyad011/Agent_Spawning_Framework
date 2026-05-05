"""Shared Streamlit UI components for all agent architectures."""

import base64
import os
from typing import Optional, Dict, Any

import streamlit as st

from utils.session_manager import SessionManager
from utils.response_parser import parse_response
from utils.plot_executor import execute_plot_code, is_plotting_code


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


def render_assistant_message(message: Dict[str, Any]) -> None:
    """
    Render assistant message with text, code blocks, and visualizations.
    
    Args:
        message: Message dict with 'content' and optional 'attachments'
    """
    content = message.get("content", "")
    attachments = message.get("attachments", [])
    
    # Parse the response to extract structured content
    parsed = parse_response(content)
    
    # Track if we've rendered anything to avoid empty sections
    has_content = False
    
    # Render text parts
    for text in parsed.text_parts:
        if text.strip():
            st.write(text)
            has_content = True
    
    # Render Python code blocks
    for code in parsed.python_blocks:
        if is_plotting_code(code):
            # Auto-execute plotting code
            with st.spinner("Rendering plot..."):
                result = execute_plot_code(code)
                
                if result["success"]:
                    # Decode and display the image
                    image_data = base64.b64decode(result["image_base64"])
                    st.image(image_data, use_container_width=True)
                    has_content = True
                else:
                    # Show code and error if execution failed
                    st.code(code, language="python")
                    st.error(f"Plot execution failed: {result['error']}")
                    has_content = True
        else:
            # Not plotting code, just display as code
            st.code(code, language="python")
            has_content = True
    
    # Render Mermaid diagrams
    if parsed.mermaid_blocks:
        try:
            from streamlit_mermaid import st_mermaid
            
            for mermaid_code in parsed.mermaid_blocks:
                st_mermaid(mermaid_code)
                has_content = True
        except ImportError:
            # Fallback if streamlit-mermaid not installed
            for mermaid_code in parsed.mermaid_blocks:
                st.code(mermaid_code, language="mermaid")
                st.warning("Install streamlit-mermaid to render diagrams: pip install streamlit-mermaid")
                has_content = True
    
    # Render SQL blocks
    for sql_code in parsed.sql_blocks:
        st.code(sql_code, language="sql")
        has_content = True
    
    # Render other code blocks
    for language, code in parsed.other_code_blocks:
        st.code(code, language=language)
        has_content = True
    
    # Render attachments from tool calls
    if attachments:
        for att in attachments:
            try:
                att_type = att.get("type")
                
                if att_type == "plot":
                    # Render plot attachment
                    if "image_base64" in att:
                        image_data = base64.b64decode(att["image_base64"])
                        st.image(image_data, use_container_width=True)
                        has_content = True
                
                elif att_type == "mermaid":
                    # Render Mermaid attachment
                    if "code" in att:
                        try:
                            from streamlit_mermaid import st_mermaid
                            st_mermaid(att["code"])
                            has_content = True
                        except ImportError:
                            st.code(att["code"], language="mermaid")
                            st.warning("Install streamlit-mermaid to render diagrams: pip install streamlit-mermaid")
                            has_content = True
            except Exception as e:
                st.error(f"Error rendering attachment: {str(e)}")
    
    # If nothing was rendered, show the raw content as fallback
    if not has_content and content:
        st.write(content)
