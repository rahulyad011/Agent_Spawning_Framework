# Runtime Agents - Notebooks

Jupyter notebooks for learning the runtime-agents codebase.

## Notebooks

| Notebook | Description |
|----------|-------------|
| **`core_concepts_code_focused.ipynb`** | Code-first, minimal text. ~15 sections, runnable examples. Best for quick hands-on learning (~30 min). |
| **`codebase_knowledge_transfer.ipynb`** | Full guide with explanations, diagrams, exercises, and troubleshooting. Best for deep understanding (~2–3 hours). |

**Tip:** Start with the code-focused notebook, then use the comprehensive one as reference.

## Setup

1. Install dependencies: `uv sync` (from project root)
2. Add your OpenAI API key to `.env`: `OPENAI_API_KEY=your-key`
3. Run Jupyter:

```bash
cd runtime-agents
uv run jupyter notebook notebooks/
```

Or: `uv run jupyter lab notebooks/`  
Or: open an `.ipynb` file in VS Code with the Jupyter extension.

## Troubleshooting

- **Kernel not found** – Select the project’s Python interpreter.
- **Module not found** – Run `uv sync` from project root.
- **OpenAI API key missing** – Set `OPENAI_API_KEY` in `.env`.

More details: project root `README.md` and `docs/`.
