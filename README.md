# Local AI Deployment Stack (Shiny Rotary Phone)

This project provides a set of automated scripts to download, manage, and deploy a modern, scalable AI stack using **vLLM**, **LiteLLM**, and **PostgreSQL**. It is designed with **airgapped environments** and **S3-compatible storage (MinIO)** in mind.

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install GitPython PyYAML requests huggingface_hub
   ```

2. **Download a Model**:
   ```bash
   python3 download-models.py google/gemma-2b-it
   ```

3. **Generate Deployment Config**:
   ```bash
   python3 deploy-models.py
   ```

4. **Launch**:
   ```bash
   docker-compose up -d
   ```

---

## 🛠️ Script Functionality

### 1. `deploy-models.py`
The core orchestration script. It scans your local models and generates a complete `docker-compose.yml` and `litellm_config.yaml`.

- **Recursive Model Discovery**: Automatically finds models containing a `config.json` inside the `model_files/` directory, supporting nested structures like `model_files/google/gemma-4-31B-it`.
- **Automated Recipes**: Clones and updates the `vllm-project/recipes` repository. It extracts optimized `--tool-call-parser` and `--reasoning-parser` flags for your models.
- **Dynamic Resource Allocation**: Calculates `gpu-memory-utilization` based on the number of models detected to prevent OOM errors.
- **Service Integration**: Configures a PostgreSQL sidecar for LiteLLM persistence (virtual keys, spend tracking).

### 2. `download-models.py`
A CLI utility to fetch models from Hugging Face and sync them with an internal listener.

- **Usage**: `python3 download-models.py <Provider>/<ModelName>`
- **CLI Arguments**: Accepts the Hugging Face repo ID as an argument.
- **Targeted Upload**: Only uploads the specific model just downloaded, preventing redundant syncs of your entire library.
- **Retry Logic**: Robust download and upload handling with configurable retries.

### 3. `docker-runai.yaml`
A template for using the **Run:ai Model Streamer** with vLLM to stream models directly from a MinIO/S3 instance.

- **Purpose**: Zero-disk model loading for instant-on capabilities.
- **Setup**: Configured for path-style addressing (MinIO) and distributed streaming across multiple GPUs.

---

## 📁 Configuration & Overrides

### Directory Structure
- `model_files/`: The root directory for your local model weights.
- `recipes/`: (Automated) Local clone of the vLLM recipes repository.
- `recipe-fallback/`: Place custom recipe YAMLs here if you want to override community defaults for parsing.
- `config/`: Place manual vLLM argument overrides here.

### Custom Arguments (`config/`)
To pass specific flags to a model (e.g., `--max-model-len`), create a file following the provider/model structure:
**File**: `config/google/gemma-4-31B-it.yaml`
```yaml
extra_args:
  - "--max-model-len"
  - "8192"
  - "--trust-remote-code"
```

---

## ❄️ Airgapped Environments

To move this stack into an isolated environment:

1. **Prepare on a connected machine**:
   - Run `download-models.py` for all desired models.
   - Run `python3 deploy-models.py` to ensure all recipes are pulled.
   - Build any custom vLLM images (see `Dockerfile` examples in session history).
   - Use `docker save` to export images and `pip download` for library wheels.
2. **Transfer**: Move the project folder, `model_files/`, and `recipes/` via USB/External drive.
3. **Load**: Run `docker load` and `pip install` from the local assets.
