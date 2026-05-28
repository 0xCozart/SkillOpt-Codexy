# Installation

## Requirements

- Python ≥ 3.10
- At least one model backend: Azure OpenAI, OpenAI, Anthropic, local Qwen, or a logged-in Codex CLI

## Quick Install

```bash
git clone https://github.com/microsoft/SkillOpt.git
cd SkillOpt
pip install -e .
```

## Optional Dependencies

Install extras for specific benchmarks or backends:

=== "ALFWorld"

    ```bash
    pip install -e ".[alfworld]"
    ```

=== "Claude Backend"

    ```bash
    pip install -e ".[claude]"
    ```

=== "Qwen (Local)"

    ```bash
    pip install -e ".[qwen]"
    ```

=== "Codex CLI"

    ```bash
    codex login
    ```

=== "WebUI"

    ```bash
    pip install -e ".[webui]"
    ```

=== "Development"

    ```bash
    pip install -e ".[dev]"
    ```

=== "All"

    ```bash
    pip install -e ".[alfworld,claude,qwen,webui,dev]"
    ```

## Environment Variables

Copy the example `.env` file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```ini
# Azure OpenAI (default backend)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key

# Or use OpenAI directly
OPENAI_API_KEY=sk-...

# Or Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
```

!!! tip
    You only need credentials for the backend you plan to use. Azure OpenAI is the default. For Codex CLI usage, `codex login` is the credential setup and no API key is required.

## Verify Installation

```bash
python -c "import skillopt; print('SkillOpt ready!')"
```

## Next Steps

→ [Run your first experiment](first-experiment.md)
