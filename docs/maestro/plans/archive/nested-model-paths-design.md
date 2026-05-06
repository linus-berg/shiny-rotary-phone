# Design Document: Support Nested Model Paths in Deployment Script

The `deploy-models.py` script currently assumes models are located in immediate subdirectories of `model_files/`. However, many models follow a `namespace/model_name` directory structure (similar to Hugging Face). This design document outlines the changes needed to support recursive model discovery and path-based deployment.

## Current State
- `deploy-models.py` uses `Path.iterdir()` to find immediate subdirectories of `model_files/`.
- Each subdirectory name is treated as the model name.
- Docker services and LiteLLM configurations are generated based on these names.

## Proposed Changes

### Recursive Discovery
The script will be updated to search for all `config.json` files within `model_files/`. The directory containing a `config.json` will be considered a model directory.

### Path Resolution
- The script will calculate the relative path from `model_files/` to the directory containing the `config.json`.
- Example: `model_files/google/gemma-4-31B-it-assistant/config.json` -> relative path `google/gemma-4-31B-it-assistant`.

### Sanitize and Deploy
- The `sanitize_name` function will be used on the full relative path (e.g., `google/gemma-4-31b-it-assistant` becomes `google-gemma-4-31b-it-assistant`).
- The vLLM service command will use the full relative path for the `--model` argument.
- LiteLLM configuration will use the sanitized name for `model_name` and the vLLM service endpoint.

## Benefits
- Supports the standard Hugging Face directory structure.
- Allows for better organization of model files.
- Prevents deployment failure when models are nested.
