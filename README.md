# Runtime Agent Spawner (Streamlit + OpenAI + uv)

A starter project for **creating (spawning) agents at runtime** based on a user request.

- **UI**: Streamlit
- **Package manager**: `uv`
- **LLM**: OpenAI (HTTP calls via `httpx`)
- **Design**: a registry of **agent templates** (roles + tool scopes). The **orchestrator** selects which templates to instantiate per request.

## Quickstart

### Prerequisites
- Python 3.11+
- `uv` installed: https://github.com/astral-sh/uv
- An OpenAI API key

### Install
```bash
cd runtime-agents-openai
uv sync
```

### Configure environment variables
Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

**Log Levels:**
- `DEBUG`: Detailed logs including routing decisions, agent execution, tool calls
- `INFO`: High-level logs (agent selection, completion status)
- `WARNING`: Only warnings and errors
- `ERROR`: Only errors

You can also change the log level in the Streamlit UI sidebar.

### Run the UI
```bash
uv run streamlit run app.py
```

## Using the app

1. Paste a requirement in the textbox.
2. Click **Run**.
3. Inspect which agents were spawned and how each contributed.

You can override model and base URL in the sidebar (API key is read from .env file by default).

## Project layout

```
runtime-agents-openai/
  app.py
  pyproject.toml
  README.md
  runtime_agents/
    llm.py            # OpenAI chat client
    tools.py          # Tool interface + demo tools + MCP adapter slot
    agents.py         # AgentTemplate + AgentInstance
    orchestrator.py   # Routing + spawning + aggregation
```

## How runtime spawning works (high level)

- **Route**: Orchestrator selects a list of template keys for the request.
- **Spawn**: For each template key, it creates an `AgentInstance` with:
  - a role-specific system prompt
  - only the tools allowed for that template
- **Run**: Agents execute (sequentially in this starter), each seeing a compact summary of prior outputs.
- **Aggregate**: A final aggregation step produces the best final answer.

## Extending this starter

### 1) Add real tool calling
Right now, agents are instructed about available tools but the starter does not automatically parse tool-call JSON.
Options:
- Implement a simple JSON tool-call schema (and execute tools when the model requests them).
- Or use OpenAI function/tool calling if you prefer.

### 2) Connect MCP tools
In `runtime_agents/tools.py`, there is an `MCPToolAdapter` placeholder. Replace it by wiring your MCP client:
- connect to an MCP server (stdio/http)
- list tools
- call tools with JSON input

Then register MCP tools in `app.py` and allow specific templates to access them.

### 3) Add parallel workers
For fan-out tasks (many docs/files/items), spawn N worker agents and run with `anyio.gather()`.

## Security notes

- Never commit your API key.
- Keep tool scopes least-privilege: only give an agent the tools it needs.
- Add budgets (max tokens / timeouts) before enabling wide fan-out.
