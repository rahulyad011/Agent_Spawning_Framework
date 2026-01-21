# Quick Reference Guide

## Switching Agent Types

### Method 1: UI Dropdown
1. Open Streamlit app
2. Look for "Agent Architecture" section in sidebar
3. Select desired agent type from dropdown
4. Changes are automatically saved to `config.yaml`

### Method 2: Config File
Edit `config.yaml`:
```yaml
agent_type: "llm_generated"  # Change this value
```

Available options:
- `template_based` - Original template-based system
- `llm_generated` - Dynamically generated agents
- `compositional` - Composed from components
- `meta` - Single adaptive agent
- `hierarchical` - Tree of agents
- `evolutionary` - Self-improving agents

## Architecture Comparison

| Architecture | Speed | Cost | Flexibility | Predictability | Best For |
|--------------|-------|------|-------------|---------------|----------|
| Template-based | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | Production |
| LLM-generated | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Research |
| Compositional | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Flexible production |
| Meta-agent | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Simple tasks |
| Hierarchical | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Complex workflows |
| Evolutionary | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Long-term learning |

## Performance Metrics

View performance comparison:
1. Run queries with different agent types
2. Click "View Performance Comparison" in sidebar
3. See metrics:
   - Average execution time
   - Average cost
   - Success rate
   - Agents spawned
   - Token usage

## Configuration Examples

### LLM-Generated Agents
```yaml
llm_generated:
  temperature: 0.7
  max_agents: 3
```

### Hierarchical Agents
```yaml
hierarchical:
  max_depth: 3
  parallel_execution: true
```

### Evolutionary Agents
```yaml
evolutionary:
  pool_size: 10
  mutation_rate: 0.1
  selection_method: "fitness_based"
```

## Troubleshooting

### Agent type not switching
- Check `config.yaml` exists and is valid YAML
- Restart Streamlit app
- Check logs for errors

### Performance metrics not showing
- Ensure performance tracking is enabled in config
- Run at least one query with the agent type
- Check `performance_metrics.json` file exists

### Import errors
- Run `uv sync` to ensure all dependencies are installed
- Check that all `__init__.py` files exist
- Verify Python path includes project root
