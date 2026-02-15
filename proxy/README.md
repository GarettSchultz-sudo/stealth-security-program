# ClawShell Proxy

AI Cost Control & Security Proxy for OpenClaw.

## Features

- **Cost Control**: Track and budget AI spending across multiple providers
- **Security Engine**: Real-time threat detection for AI agent interactions
- **Smart Routing**: Intelligent model selection based on cost and performance
- **Budget Management**: Enforce spending limits at organization and agent levels

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check app/
ruff format app/

# Run type checking
mypy app/ --ignore-missing-imports
```

## License

MIT
