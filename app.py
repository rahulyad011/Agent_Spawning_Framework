import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime
from io import StringIO
from pathlib import Path

import anyio
import streamlit as st
from dotenv import load_dotenv

from runtime_agents.logger import get_logger

logger = get_logger(__name__)

from runtime_agents.agents import AgentTemplate
from runtime_agents.db_tools import (
    DatabaseConnectionTool,
    DatabaseQueryTool,
    SchemaIntrospectionTool,
)
from runtime_agents.image_tools import ImageAnalysisTool, ImageListTool
from runtime_agents.llm import OpenAIChatClient
from runtime_agents.orchestrator import Orchestrator
from runtime_agents.session import SessionManager
from runtime_agents.tools import FileListTool, FileReadTool, HttpGetTool, TimeTool

# Load environment variables from .env file
load_dotenv()

# Initialize session manager
session_manager = SessionManager()


def mask_key(key: str) -> str:
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


st.set_page_config(page_title="Runtime Agent Spawner (OpenAI)", layout="wide")

st.title("Runtime Agent Spawner (OpenAI)")
st.caption(
    "Conversational agent spawning: orchestrator selects agent templates, spawns instances, and aggregates results."
)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "session_manager" not in st.session_state:
    st.session_state.session_manager = session_manager
if "db_connection_tool" not in st.session_state:
    st.session_state.db_connection_tool = DatabaseConnectionTool()

# Read env defaults from .env file
ENV_KEY = os.getenv("OPENAI_API_KEY")
ENV_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ENV_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")

with st.sidebar:
    st.header("Session Management")
    # Session selector
    existing_sessions = session_manager.list_sessions()
    if existing_sessions:
        selected_session = st.selectbox(
            "Load existing session",
            ["-- New Session --"] + existing_sessions,
            key="session_selector",
        )
        if selected_session != "-- New Session --":
            if st.button("Load Session"):
                session = session_manager.load_session(selected_session)
                if session:
                    st.session_state.session_id = session.session_id
                    st.rerun()

    if st.button("New Session"):
        new_session = session_manager.create_session()
        st.session_state.session_id = new_session.session_id
        st.rerun()

    if st.session_state.session_id:
        if st.button("Delete Current Session"):
            session_manager.delete_session(st.session_state.session_id)
            st.session_state.session_id = None
            st.rerun()

    st.divider()

    st.header("OpenAI Settings")
    st.write(f"API key (.env OPENAI_API_KEY): {mask_key(ENV_KEY) if ENV_KEY else '(not set)'}")

    api_key = st.text_input(
        "API key override (optional)",
        type="password",
        value="",
        help="Leave blank to use OPENAI_API_KEY from the .env file.",
    )
    model = st.text_input("Model", value=ENV_MODEL)
    base_url = st.text_input("Base URL", value=ENV_BASE)

    st.divider()

    st.header("File Upload")
    uploaded_files = st.file_uploader(
        "Upload files",
        type=["txt", "pdf", "csv", "json", "md", "py", "log"],
        accept_multiple_files=True,
    )

    st.divider()

    st.header("Image Upload")
    uploaded_images = st.file_uploader(
        "Upload images",
        type=["png", "jpg", "jpeg", "gif", "webp"],
        accept_multiple_files=True,
        key="image_uploader",
    )

    st.divider()

    st.header("Database Connection")
    db_type = st.selectbox("Database Type", ["postgresql", "mysql", "sqlite"])
    db_connection_string = st.text_input(
        "Connection String",
        type="password",
        help="e.g., postgresql://user:pass@host:port/dbname",
    )
    if st.button("Connect to Database"):
        if db_connection_string:
            connection_id = f"db_{uuid.uuid4().hex[:8]}"
            # Use anyio.run for async call
            async def connect_db():
                return await st.session_state.db_connection_tool.__call__(
                    {
                        "connection_string": db_connection_string,
                        "db_type": db_type,
                        "connection_id": connection_id,
                    }
                )

            result = anyio.run(connect_db)
            if "error" not in result:
                st.success(f"Connected! Connection ID: {connection_id}")
                # Store connection in session
                if st.session_state.session_id:
                    session = session_manager.load_session(st.session_state.session_id)
                    if session:
                        from runtime_agents.session import DBConnection

                        session.db_connections.append(
                            DBConnection(
                                connection_id=connection_id,
                                db_type=db_type,
                                connection_string=db_connection_string,
                            )
                        )
                        session_manager.save_session(session)
                        st.rerun()
            else:
                st.error(f"Connection failed: {result.get('error')}")

    st.divider()
    st.subheader("Debug Logs")
    current_log_level = os.getenv("LOG_LEVEL", "DEBUG")
    log_level = st.selectbox("Log Level", ["DEBUG", "INFO", "WARNING", "ERROR"], 
                             index=["DEBUG", "INFO", "WARNING", "ERROR"].index(current_log_level) if current_log_level in ["DEBUG", "INFO", "WARNING", "ERROR"] else 0)
    if st.button("Update Log Level"):
        os.environ["LOG_LEVEL"] = log_level
        logger.setLevel(getattr(logging, log_level, logging.DEBUG))
        for handler in logger.handlers:
            handler.setLevel(getattr(logging, log_level, logging.DEBUG))
        st.success(f"Log level updated to {log_level}")
        st.rerun()

    st.divider()
    st.subheader("Notes")
    st.write(
        "This starter uses the Chat Completions endpoint (`/v1/chat/completions`).\n"
        "If you're using an OpenAI-compatible gateway (vLLM/LiteLLM), set Base URL accordingly."
    )
    st.write(
        f"**Log Level**: Set via LOG_LEVEL environment variable or use the dropdown above. "
        f"Current: {os.getenv('LOG_LEVEL', 'DEBUG')}"
    )

# Ensure we have a session
if not st.session_state.session_id:
    session = session_manager.create_session()
    st.session_state.session_id = session.session_id

# Load current session
current_session = session_manager.load_session(st.session_state.session_id)
if not current_session:
    current_session = session_manager.create_session()
    st.session_state.session_id = current_session.session_id

# Handle file uploads
if uploaded_files:
    uploads_dir = session_manager.get_session_uploads_dir(current_session.session_id)
    for uploaded_file in uploaded_files:
        # Check if file already exists
        file_path = uploads_dir / "files" / uploaded_file.name
        if not file_path.exists():
            # Save file
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Add to session
            from runtime_agents.session import FileMetadata

            file_metadata = FileMetadata(
                filename=uploaded_file.name,
                file_path=str(file_path),
                file_type=uploaded_file.type or "unknown",
                size_bytes=len(uploaded_file.getbuffer()),
                uploaded_at=datetime.utcnow().isoformat(),
            )
            current_session.files.append(file_metadata)
            session_manager.save_session(current_session)
            st.success(f"Uploaded: {uploaded_file.name}")
            st.rerun()

# Handle image uploads
if uploaded_images:
    uploads_dir = session_manager.get_session_uploads_dir(current_session.session_id)
    for uploaded_image in uploaded_images:
        # Check if image already exists
        image_path = uploads_dir / "images" / uploaded_image.name
        if not image_path.exists():
            # Save image
            with open(image_path, "wb") as f:
                f.write(uploaded_image.getbuffer())

            # Add to session
            from runtime_agents.session import ImageMetadata

            image_metadata = ImageMetadata(
                filename=uploaded_image.name,
                file_path=str(image_path),
                image_format=uploaded_image.type or "unknown",
                size_bytes=len(uploaded_image.getbuffer()),
                uploaded_at=datetime.utcnow().isoformat(),
            )
            current_session.images.append(image_metadata)
            session_manager.save_session(current_session)
            st.success(f"Uploaded image: {uploaded_image.name}")
            st.rerun()

key_in_use = api_key.strip() or ENV_KEY
if not key_in_use:
    st.warning("Set OPENAI_API_KEY in your .env file (or provide a key in the sidebar) to run.")

# Display chat history
st.subheader("Chat")
chat_container = st.container()

with chat_container:
    for message in current_session.chat_history:
        role = message["role"]
        content = message["content"]
        with st.chat_message(role):
            st.write(content)

# Display current session info
if st.session_state.session_id:
    st.info(f"Session: {st.session_state.session_id}")

# Chat input
user_input = st.chat_input("Enter your message...", disabled=not bool(key_in_use))

if user_input and key_in_use:
    # Add user message to session
    current_session.add_message("user", user_input)
    session_manager.save_session(current_session)

    # Display user message
    with st.chat_message("user"):
        st.write(user_input)

    # Prepare tools with session context
    uploads_dir = session_manager.get_session_uploads_dir(current_session.session_id)
    file_read_tool = FileReadTool(session_uploads_dir=uploads_dir)
    file_list_tool = FileListTool(
        session_files=[asdict(f) for f in current_session.files]
    )

    # Database tools
    schema_tool = SchemaIntrospectionTool(
        connection_tool=st.session_state.db_connection_tool
    )
    query_tool = DatabaseQueryTool(connection_tool=st.session_state.db_connection_tool)

    # Image tools
    image_analysis_tool = ImageAnalysisTool(session_uploads_dir=uploads_dir)
    image_list_tool = ImageListTool(
        session_images=[asdict(img) for img in current_session.images]
    )

    # Tool registry
    tools = {
        "time_now": TimeTool(),
        "http_get": HttpGetTool(),
        "file_read": file_read_tool,
        "file_list": file_list_tool,
        "db_schema": schema_tool,
        "db_query": query_tool,
        "image_analyze": image_analysis_tool,
        "image_list": image_list_tool,
    }

    # Agent templates
    registry = {
        "planner": AgentTemplate(
            key="planner",
            name="Planner",
            system_prompt="You break down the request into an execution plan and identify missing info.",
            tool_names=["time_now", "file_list", "image_list"],
        ),
        "researcher": AgentTemplate(
            key="researcher",
            name="Researcher",
            system_prompt=(
                "You gather references and factual details. "
                "If you need to fetch a URL, ask for it (or use http_get if available and appropriate)."
            ),
            tool_names=["http_get", "file_read"],
        ),
        "analyst": AgentTemplate(
            key="analyst",
            name="Analyst",
            system_prompt="You analyze tradeoffs, compare options, and produce structured reasoning.",
            tool_names=["file_read", "db_schema", "db_query"],
        ),
        "writer": AgentTemplate(
            key="writer",
            name="Writer",
            system_prompt="You write clean, concise outputs tailored to the request.",
            tool_names=["file_read"],
        ),
    }

    # Build detailed context from session for agents
    session_context_parts = []
    
    if current_session.files:
        file_list = "\n".join([
            f"  - {f.filename} ({f.file_type}, {f.size_bytes} bytes)"
            for f in current_session.files
        ])
        session_context_parts.append(f"Uploaded files available:\n{file_list}\nYou can use the 'file_read' tool to read any of these files.")
    
    if current_session.images:
        image_list = "\n".join([
            f"  - {img.filename} ({img.image_format}, {img.size_bytes} bytes)"
            for img in current_session.images
        ])
        session_context_parts.append(f"Uploaded images available:\n{image_list}\nYou can use the 'image_analyze' tool to analyze any of these images.")
    
    if current_session.db_connections:
        db_info = []
        for db_conn in current_session.db_connections:
            db_info.append(f"  - Connection ID: {db_conn.connection_id}, Type: {db_conn.db_type}")
            if db_conn.selected_tables:
                db_info.append(f"    Selected tables: {', '.join(db_conn.selected_tables)}")
        session_context_parts.append(
            f"Database connections available:\n" + "\n".join(db_info) + 
            "\nYou can use 'db_schema' to inspect table structures and 'db_query' to query data."
        )

    # Build session context string
    session_context = ""
    if session_context_parts:
        session_context = "Available resources:\n" + "\n\n".join(session_context_parts)

    # Add conversation history context
    if len(current_session.chat_history) > 1:
        recent_messages = current_session.chat_history[-5:-1]  # Last 4 messages (excluding current)
        if recent_messages:
            history_text = "\n".join([
                f"{msg['role']}: {msg['content'][:200]}..." if len(msg['content']) > 200 else f"{msg['role']}: {msg['content']}"
                for msg in recent_messages
            ])
            session_context += "\n\nRecent conversation history:\n" + history_text

    # Create LLM client
    client = OpenAIChatClient(api_key=key_in_use, model=model, base_url=base_url)

    # Set LLM client for image analysis
    image_analysis_tool.llm_client = client

    # Create orchestrator with session context
    orch = Orchestrator(llm=client, registry=registry, tools=tools, session_context=session_context)

    # Prepare requirement (user input only, context goes to orchestrator)
    requirement = user_input

    # Run orchestrator
    with st.chat_message("assistant"):
        with st.spinner("Running agents..."):
            try:
                logger.info(f"[APP] Starting orchestrator for user input: {user_input[:100]}...")
                agent_results, final = anyio.run(orch.run, requirement)
                logger.info(f"[APP] Orchestrator completed successfully")

                # Display final answer
                st.write(final)

                # Add assistant message to session
                current_session.add_message("assistant", final)
                session_manager.save_session(current_session)

                # Show agent details in expander
                with st.expander("Agent Details", expanded=False):
                    for r in agent_results:
                        st.write(f"**{r.agent_name}**:")
                        st.write(r.output)
                        st.divider()

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                current_session.add_message("assistant", error_msg)
                session_manager.save_session(current_session)
