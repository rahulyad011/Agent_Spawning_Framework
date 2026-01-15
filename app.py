import os

import anyio
import streamlit as st
from dotenv import load_dotenv

from runtime_agents.agents import AgentTemplate
from runtime_agents.llm import OpenAIChatClient
from runtime_agents.orchestrator import Orchestrator
from runtime_agents.tools import HttpGetTool, TimeTool

# Load environment variables from .env file
load_dotenv()


def mask_key(key: str) -> str:
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


st.set_page_config(page_title="Runtime Agent Spawner (OpenAI)", layout="wide")

st.title("Runtime Agent Spawner (OpenAI)")
st.caption("Runtime agent spawning demo: orchestrator selects agent templates, spawns instances, and aggregates results.")

# Read env defaults from .env file
ENV_KEY = os.getenv("OPENAI_API_KEY")
ENV_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ENV_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")

with st.sidebar:
    st.header("OpenAI Settings")
    st.write(f"API key (.env OPENAI_API_KEY): {mask_key(ENV_KEY)}")

    api_key = st.text_input(
        "API key override (optional)",
        type="password",
        value="",
        help="Leave blank to use OPENAI_API_KEY from the .env file.",
    )
    model = st.text_input("Model", value=ENV_MODEL)
    base_url = st.text_input("Base URL", value=ENV_BASE)

    st.divider()
    st.subheader("Notes")
    st.write(
        "This starter uses the Chat Completions endpoint (`/v1/chat/completions`).\n"
        "If you're using an OpenAI-compatible gateway (vLLM/LiteLLM), set Base URL accordingly."
    )

key_in_use = api_key.strip() or ENV_KEY
if not key_in_use:
    st.warning("Set OPENAI_API_KEY in your .env file (or provide a key in the sidebar) to run.")

# Tool registry (demo). Replace/extend with MCPToolAdapter wrappers later.
tools = {
    "time_now": TimeTool(),
    "http_get": HttpGetTool(),
}

# Agent templates (fixed catalog; spawned dynamically per request)
registry = {
    "planner": AgentTemplate(
        key="planner",
        name="Planner",
        system_prompt="You break down the request into an execution plan and identify missing info.",
        tool_names=["time_now"],
    ),
    "researcher": AgentTemplate(
        key="researcher",
        name="Researcher",
        system_prompt=(
            "You gather references and factual details. "
            "If you need to fetch a URL, ask for it (or use http_get if available and appropriate)."
        ),
        tool_names=["http_get"],
    ),
    "analyst": AgentTemplate(
        key="analyst",
        name="Analyst",
        system_prompt="You analyze tradeoffs, compare options, and produce structured reasoning.",
        tool_names=[],
    ),
    "writer": AgentTemplate(
        key="writer",
        name="Writer",
        system_prompt="You write clean, concise outputs tailored to the request.",
        tool_names=[],
    ),
}

req = st.text_area(
    "Enter a requirement / task",
    height=160,
    placeholder="e.g., Compare static orchestrator vs dynamic spawning and recommend a path.",
)
run = st.button("Run", type="primary", disabled=not bool(key_in_use))

if run and req.strip():
    client = OpenAIChatClient(api_key=key_in_use, model=model, base_url=base_url)
    orch = Orchestrator(llm=client, registry=registry, tools=tools)

    with st.spinner("Running agents..."):
        agent_results, final = anyio.run(orch.run, req)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Spawned Agents + Outputs")
        for r in agent_results:
            with st.expander(r.agent_name, expanded=False):
                st.write(r.output)

    with col2:
        st.subheader("Final Answer")
        st.write(final)
