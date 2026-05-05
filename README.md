# Runtime Agent Spawner (Multi-Architecture)

A comprehensive agent system supporting **6 different agent architectures** for runtime agent spawning and orchestration. Compare performance and capabilities across template-based, LLM-generated, compositional, meta, hierarchical, and evolutionary approaches.

- **UI**: Streamlit
- **Package manager**: `uv`
- **LLM**: OpenAI (HTTP calls via `httpx`)
- **Architectures**: 6 different agent spawning approaches
- **Design**: Compare and evaluate different agent architectures side-by-side

## Quickstart

### Prerequisites
- Python 3.11+
- `uv` installed: https://github.com/astral-sh/uv
- An OpenAI API key

### Install
```bash
cd runtime-agents
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

### Configure Agent Type
Edit `config.yaml` to select which agent architecture to use:

```yaml
agent_type: "template_based"  # Options: template_based, llm_generated, compositional, meta, hierarchical, evolutionary
```

Or use the dropdown in the Streamlit UI sidebar to switch agent types dynamically.

### Run the UI
```bash
uv run streamlit run app.py
```

## Agent Architectures

### 1. Template-Based (Default)
- **Description**: Predefined agent templates with dynamic selection
- **Pros**: Predictable, fast, secure, cost-effective
- **Cons**: Limited flexibility, requires code changes for new agents
- **Best for**: Production systems, well-defined use cases

### 2. LLM-Generated
- **Description**: Agents generated dynamically by LLM for each request
- **Pros**: Fully adaptive, no predefined roles needed
- **Cons**: Higher cost, less predictable, slower
- **Best for**: Research, exploration, novel tasks

### 3. Compositional
- **Description**: Agents built by composing reusable components
- **Pros**: Flexible yet controlled, reusable components
- **Cons**: Requires component library
- **Best for**: Multi-domain applications, flexible but controlled scenarios

### 4. Meta-Agent
- **Description**: Single adaptive agent that adapts per request
- **Pros**: Simple, fast, no agent creation overhead
- **Cons**: Less specialized, harder to parallelize
- **Best for**: Simple scenarios, when latency is critical

### 5. Hierarchical
- **Description**: Tree of agents that decompose tasks hierarchically
- **Pros**: Handles complex workflows, can parallelize
- **Cons**: Complex orchestration, higher cost
- **Best for**: Complex multi-step workflows, research projects

### 6. Evolutionary
- **Description**: Agents evolve and adapt based on performance feedback
- **Pros**: Self-improving, learns from experience
- **Cons**: Requires feedback mechanism, needs time to learn
- **Best for**: Long-running systems, personalized agents

## Using the app

1. Select agent architecture from sidebar dropdown
2. Upload files/images or connect to databases (optional)
3. Enter your requirement in the chat
4. View results and performance metrics
5. Compare performance across different architectures

You can switch agent types dynamically and compare their performance using the Performance Comparison view.

## Project layout

```
runtime-agents/
  app.py                          # Main UI (agent-type agnostic)
  config.yaml                     # Agent type selection & settings
  pyproject.toml                  # Dependencies (with optional comments)
  README.md
  utils/                          # Shared utilities
    session_manager.py            # Session management
    tool_registry.py             # Shared tool definitions
    ui_components.py             # Shared Streamlit UI components
    performance_tracker.py       # Performance metrics & comparison
    agent_factory.py             # Factory for creating orchestrators
  runtime_agents/
    template_based/              # Template-based architecture (original)
      agents.py
      orchestrator.py
    shared/                      # Shared across all architectures
      base.py                    # Base classes/interfaces
      llm.py                     # LLM client
      logger.py                  # Logging
      tools.py                   # Tool definitions
      db_tools.py                # Database tools
      image_tools.py             # Image tools
  runtime_agents_llm_generated/  # LLM-generated agents
    generator.py
    orchestrator.py
  runtime_agents_compositional/  # Compositional building
    components.py
    composer.py
    orchestrator.py
  runtime_agents_meta/           # Meta-agent
    meta_agent.py
    prompt_builder.py
    tool_selector.py
    orchestrator.py
  runtime_agents_hierarchical/   # Hierarchical networks
    parent_agent.py
    task_decomposer.py
    orchestrator.py
  runtime_agents_evolutionary/   # Evolutionary system
    agent_pool.py
    fitness_evaluator.py
    mutation_engine.py
    orchestrator.py
  docs/                          # Documentation
    understanding.md             # System architecture
    improvement_ideas.md         # POC roadmap
    alternative_approaches.md    # Architecture comparisons
```

## Performance Comparison

The system tracks performance metrics for all agent types:
- Execution time
- Token usage
- Cost estimates
- Number of agents spawned
- Tool usage patterns
- Success rates

View comparison statistics in the sidebar or use the Performance Comparison view.

## Configuration

### Agent-Specific Settings

Edit `config.yaml` to configure each architecture:

```yaml
agent_type: "template_based"

template_based:
  use_llm_routing: true
  
llm_generated:
  temperature: 0.7
  max_agents: 3
  
compositional:
  component_library_path: "components/"
  
meta:
  adaptive_prompting: true
  
hierarchical:
  max_depth: 3
  parallel_execution: true
  
evolutionary:
  pool_size: 10
  mutation_rate: 0.1
```

## Dependencies

Core dependencies are always installed. Optional dependencies are commented in `pyproject.toml`:
- `numpy`, `scipy` - For evolutionary system (uncomment if needed)
- `matplotlib`, `plotly` - For performance charts (uncomment if needed)

## Security notes

- Never commit your API key.
- Keep tool scopes least-privilege: only give an agent the tools it needs.
- Add budgets (max tokens / timeouts) before enabling wide fan-out.
- Database connections are stored in session files (consider encryption for production).

## Documentation

- `docs/understanding.md` - How the current system works
- `docs/improvement_ideas.md` - POC roadmap and improvements
- `docs/alternative_approaches.md` - Detailed comparison of all architectures