import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import anyio
import streamlit as st
import yaml
from dotenv import load_dotenv

from runtime_agents.shared.llm import OpenAIChatClient
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.db_tools import DatabaseConnectionTool
from utils.agent_factory import AgentFactory
from utils.performance_tracker import PerformanceTracker
from utils.session_manager import SessionManager
from utils.tool_registry import get_default_tools
from utils.ui_components import (
    mask_key,
    render_file_upload,
    render_sidebar_settings,
    render_assistant_message,
)

logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize session manager
session_manager = SessionManager()

# Initialize agent factory
agent_factory = AgentFactory()

# Initialize performance tracker
performance_tracker = PerformanceTracker()

st.set_page_config(page_title="Runtime Agent Spawner (OpenAI)", layout="wide")

st.title("Runtime Agent Spawner (OpenAI)")
st.caption(
    "Multi-architecture agent system: Compare template-based, LLM-generated, compositional, meta, hierarchical, and evolutionary agents."
)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "session_manager" not in st.session_state:
    st.session_state.session_manager = session_manager
if "db_connection_tool" not in st.session_state:
    st.session_state.db_connection_tool = DatabaseConnectionTool()
if "agent_type" not in st.session_state:
    st.session_state.agent_type = agent_factory.config.get("agent_type", "template_based")

# Read env defaults from .env file
ENV_KEY = os.getenv("OPENAI_API_KEY")
ENV_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ENV_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")

with st.sidebar:
    # Agent type selector
    st.header("Agent Architecture")
    agent_types = [
        "template_based",
        "llm_generated",
        "compositional",
        "meta",
        "hierarchical",
        "evolutionary",
    ]
    selected_agent_type = st.selectbox(
        "Select Agent Type",
        agent_types,
        index=agent_types.index(st.session_state.agent_type) if st.session_state.agent_type in agent_types else 0,
        help="Choose which agent architecture to use",
    )
    if selected_agent_type != st.session_state.agent_type:
        st.session_state.agent_type = selected_agent_type
        st.info(f"Switched to {selected_agent_type} architecture")
        # Update config file
        try:
            config_path = Path("config.yaml")
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f) or {}
                config["agent_type"] = selected_agent_type
                with open(config_path, "w") as f:
                    yaml.dump(config, f)
        except Exception as e:
            logger.warning(f"Could not update config: {e}")

    st.divider()

    # Session management and settings
    api_key, model, base_url = render_sidebar_settings(
        session_manager, ENV_MODEL, ENV_BASE
    )

    # File and image uploads
    uploaded_files, uploaded_images = render_file_upload()

    # Database connection UI
    st.divider()
    st.header("Database Connection")
    db_type = st.selectbox("Database Type", ["postgresql", "mysql", "sqlite"])
    db_connection_string = st.sidebar.text_input(
        "Connection String",
        type="password",
        help="e.g., postgresql://user:pass@host:port/dbname",
    )
    if st.button("Connect to Database"):
        if db_connection_string:
            connection_id = f"db_{uuid.uuid4().hex[:8]}"
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
                if st.session_state.session_id:
                    session = session_manager.load_session(st.session_state.session_id)
                    if session:
                        from utils.session_manager import DBConnection

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
    log_level = st.selectbox(
        "Log Level",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        index=["DEBUG", "INFO", "WARNING", "ERROR"].index(current_log_level)
        if current_log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
        else 0,
    )
    if st.button("Update Log Level"):
        os.environ["LOG_LEVEL"] = log_level
        logger.setLevel(getattr(logging, log_level, logging.DEBUG))
        for handler in logger.handlers:
            handler.setLevel(getattr(logging, log_level, logging.DEBUG))
        st.success(f"Log level updated to {log_level}")
        st.rerun()

    st.divider()
    st.subheader("Performance Metrics")
    if st.button("View Performance Comparison"):
        st.session_state.show_performance = True

    st.divider()
    st.subheader("Notes")
    st.write(
        "This app supports 6 agent architectures. Switch between them using the dropdown above."
    )
    st.write(
        f"**Current Agent Type**: {st.session_state.agent_type.replace('_', ' ').title()}"
    )
    st.write(
        f"**Log Level**: {os.getenv('LOG_LEVEL', 'DEBUG')}"
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
        file_path = uploads_dir / "files" / uploaded_file.name
        if not file_path.exists():
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            from utils.session_manager import FileMetadata

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
        image_path = uploads_dir / "images" / uploaded_image.name
        if not image_path.exists():
            with open(image_path, "wb") as f:
                f.write(uploaded_image.getbuffer())

            from utils.session_manager import ImageMetadata

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
        with st.chat_message(role):
            if role == "assistant":
                # Use enhanced rendering for assistant messages
                render_assistant_message(message)
            else:
                # Simple rendering for user messages
                st.write(message["content"])

# Display current session info
if st.session_state.session_id:
    st.info(f"Session: {st.session_state.session_id} | Agent Type: {st.session_state.agent_type.replace('_', ' ').title()}")

# Performance comparison view
if st.session_state.get("show_performance", False):
    st.subheader("Performance Comparison")
    comparison = performance_tracker.get_comparison_stats()
    if comparison:
        import pandas as pd

        df = pd.DataFrame(comparison).T
        st.dataframe(df)
    else:
        st.info("No performance data yet. Run some queries to collect metrics.")
    if st.button("Close Performance View"):
        st.session_state.show_performance = False

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
    tools = get_default_tools(
        session_uploads_dir=uploads_dir,
        session_files=[asdict(f) for f in current_session.files],
        session_images=[asdict(img) for img in current_session.images],
        db_connection_tool=st.session_state.db_connection_tool,
    )

    # Set LLM client for image analysis tool
    client = OpenAIChatClient(api_key=key_in_use, model=model, base_url=base_url)
    if "image_analyze" in tools:
        tools["image_analyze"].llm_client = client

    # Build session context
    session_context_parts = []

    if current_session.files:
        file_list = "\n".join(
            [
                f"  - {f.filename} ({f.file_type}, {f.size_bytes} bytes)"
                for f in current_session.files
            ]
        )
        session_context_parts.append(
            f"Uploaded files available:\n{file_list}\nYou can use the 'file_read' tool to read any of these files."
        )

    if current_session.images:
        image_list = "\n".join(
            [
                f"  - {img.filename} ({img.image_format}, {img.size_bytes} bytes)"
                for img in current_session.images
            ]
        )
        session_context_parts.append(
            f"Uploaded images available:\n{image_list}\nYou can use the 'image_analyze' tool to analyze any of these images."
        )

    if current_session.db_connections:
        db_info = []
        for db_conn in current_session.db_connections:
            db_info.append(
                f"  - Connection ID: {db_conn.connection_id}, Type: {db_conn.db_type}"
            )
            if db_conn.selected_tables:
                db_info.append(
                    f"    Selected tables: {', '.join(db_conn.selected_tables)}"
                )
        session_context_parts.append(
            f"Database connections available:\n"
            + "\n".join(db_info)
            + "\nYou can use 'db_schema' to inspect table structures and 'db_query' to query data."
        )

    session_context = ""
    if session_context_parts:
        session_context = "Available resources:\n" + "\n\n".join(session_context_parts)

    if len(current_session.chat_history) > 1:
        recent_messages = current_session.chat_history[-5:-1]
        if recent_messages:
            history_text = "\n".join(
                [
                    f"{msg['role']}: {msg['content'][:200]}..."
                    if len(msg["content"]) > 200
                    else f"{msg['role']}: {msg['content']}"
                    for msg in recent_messages
                ]
            )
            session_context += "\n\nRecent conversation history:\n" + history_text

    # Create orchestrator using factory
    try:
        orch = agent_factory.create_orchestrator(
            llm=client,
            tools=tools,
            session_context=session_context,
            agent_type=st.session_state.agent_type,
        )

        # Run orchestrator with performance tracking
        with st.chat_message("assistant"):
            with st.spinner(f"Running {st.session_state.agent_type.replace('_', ' ')} agents..."):
                try:
                    performance_tracker.start_execution()
                    logger.info(
                        f"[APP] Starting {st.session_state.agent_type} orchestrator for: {user_input[:100]}..."
                    )

                    agent_results, final = anyio.run(orch.run, user_input)

                    execution_time = performance_tracker.get_execution_time()
                    metrics = orch.get_metrics()

                    # Record metrics
                    if performance_tracker:
                        performance_tracker.record_execution(
                            agent_type=st.session_state.agent_type,
                            execution_time=execution_time,
                            token_usage=metrics.token_usage,
                            cost_estimate=metrics.cost_estimate,
                            num_agents_spawned=metrics.num_agents_spawned,
                            tool_calls_count=metrics.tool_calls_count,
                        )
                        performance_tracker.save_metrics()

                    logger.info(f"[APP] Orchestrator completed successfully")

                    # Collect visualization attachments from tool results
                    attachments = []
                    for agent_result in agent_results:
                        for tool_call in agent_result.tool_calls:
                            tool_name = tool_call.get("tool")
                            result = tool_call.get("result", {})
                            
                            # Check for render_plot or render_mermaid tool results
                            if tool_name == "render_plot" and result.get("type") == "plot":
                                if "image_base64" in result and not result.get("error"):
                                    attachments.append({
                                        "type": "plot",
                                        "image_base64": result["image_base64"],
                                        "format": result.get("format", "png")
                                    })
                            elif tool_name == "render_mermaid" and result.get("type") == "mermaid":
                                if "code" in result and not result.get("error"):
                                    attachments.append({
                                        "type": "mermaid",
                                        "code": result["code"]
                                    })
                    
                    # Create message dict with content and attachments
                    message_dict = {"role": "assistant", "content": final}
                    if attachments:
                        message_dict["attachments"] = attachments
                    
                    # Display final answer with visualizations
                    render_assistant_message(message_dict)

                    # Add assistant message to session with attachments
                    current_session.add_message("assistant", final, attachments=attachments if attachments else None)
                    session_manager.save_session(current_session)

                    # Show agent details in expander
                    with st.expander("Agent Details", expanded=False):
                        for r in agent_results:
                            st.write(f"**{r.agent_name}**:")
                            st.write(r.output)
                            if r.tool_calls:
                                st.write(f"*Tool calls: {len(r.tool_calls)}*")
                            st.divider()

                    # Show performance metrics
                    with st.expander("Performance Metrics", expanded=False):
                        st.write(f"**Execution Time**: {execution_time:.2f}s")
                        st.write(f"**Agents Spawned**: {metrics.num_agents_spawned}")
                        st.write(f"**Tool Calls**: {metrics.tool_calls_count}")

                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"[APP] Error: {e}", exc_info=True)
                    current_session.add_message("assistant", error_msg)
                    session_manager.save_session(current_session)

                    # Record failed execution
                    if performance_tracker:
                        performance_tracker.record_execution(
                            agent_type=st.session_state.agent_type,
                            execution_time=performance_tracker.get_execution_time(),
                            token_usage={"input_tokens": 0, "output_tokens": 0},
                            cost_estimate=0.0,
                            num_agents_spawned=0,
                            tool_calls_count=0,
                            success=False,
                            error_message=str(e),
                        )

    except Exception as e:
        st.error(f"Failed to create orchestrator: {str(e)}")
        logger.error(f"[APP] Factory error: {e}", exc_info=True)
