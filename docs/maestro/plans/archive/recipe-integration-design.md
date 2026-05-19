# Design Document: Automated vLLM Configuration via Recipes Repository

This design enables `deploy-models.py` to leverage optimized model configurations from the `vllm-project/recipes` repository.

## Requirements
- Automatically clone or pull the `vllm-project/recipes` repository using `GitPython`.
- Dynamically extract `--tool-call-parser` and `--reasoning-parser` (and other recommended flags) from recipe YAMLs.
- Apply these configurations to the generated `docker-compose.yml`.
- Provide a local `config/` directory for manual overrides.

## Components

### Repository Manager
A module within the script that uses `GitPython` to ensure the `recipes/` directory is present and up-to-date with the latest optimized recipes from the community.

### Recipe Parser
A logic block that:
1. Maps a local model path (e.g., `google/gemma-4-31B-it`) to a recipe filename (`gemma-4-31B-it.yaml`).
2. Searches recursively in `recipes/models/` and `config/`.
3. Parses the YAML to extract specific command-line arguments under `features -> tool_calling` and `features -> reasoning`.

### Configuration Injector
Updates the vLLM service definition in the internal dictionary representation of the Docker Compose file before serialization.
