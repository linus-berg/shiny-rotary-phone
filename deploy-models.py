#!/usr/bin/python3
import os
import re
from pathlib import Path

def sanitize_name(name):
    """
    Converts folder names into valid, lowercase Docker service names.
    (e.g., 'Meta-Llama-3_8B' -> 'meta-llama-3-8b')
    """
    safe_name = re.sub(r'[^a-zA-Z0-9-]', '-', name).lower()
    return re.sub(r'-+', '-', safe_name).strip('-')

def generate_configs(base_dir="./model_files"):
    print(f"Scanning directory: {base_dir}")
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"❌ Error: Directory '{base_dir}' does not exist.")
        return

    # Find all directories containing config.json recursively
    models = []
    for config_file in base_path.rglob('config.json'):
        # Get the relative path from base_path to the directory containing config.json
        model_rel_path = config_file.parent.relative_to(base_path)
        models.append(str(model_rel_path))

    if not models:
        print(f"❌ No model folders containing 'config.json' found in '{base_dir}'.")
        return

    print(f"✅ Found {len(models)} models: {', '.join(models)}\n")

    # ==========================================
    # 1. Calculate GPU Memory Utilization
    # ==========================================
    # vLLM limits need to be scaled dynamically. 
    # Total combined shouldn't exceed ~0.9.
    gpu_util = round(0.9 / len(models), 2)
    print(f"Allocating {gpu_util} VRAM utilization per model.\n")

    if gpu_util < 0.2:
        print("⚠️ Warning: You have many models. A VRAM allocation below 0.2 per model")
        print("may cause vLLM to fail during boot due to insufficient KV Cache space.")

    # ==========================================
    # 2. Generate litellm_config.yaml
    # ==========================================
    litellm_yaml = "model_list:\n"
    
    for model_folder in models:
        safe_name = sanitize_name(model_folder)
        litellm_yaml += f"""  - model_name: {safe_name}
    litellm_params:
      model: openai/{safe_name}
      api_base: http://vllm-{safe_name}:8000/v1
      api_key: "sk-dummy-key"
"""

    with open("litellm_config.yaml", "w") as f:
        f.write(litellm_yaml)
    print("✅ Generated: litellm_config.yaml")

    # ==========================================
    # 3. Generate docker-compose.yml
    # ==========================================
    compose_yaml = "services:\n"
    
    # Generate vLLM services dynamically
    for i, model_folder in enumerate(models):
        safe_name = sanitize_name(model_folder)
        host_port = 8000 + i  # Increment host port starting from 8000
        
        compose_yaml += f"""
  vllm-{safe_name}:
    image: vllm/vllm-openai:latest
    container_name: vllm-{safe_name}
    ports:
      - "{host_port}:8000"
    volumes:
      - ./model_files:/model_files
    command: 
      - "--model"
      - "/model_files/{model_folder}"
      - "--host"
      - "0.0.0.0"
      - "--port"
      - "8000"
      - "--served-model-name"
      - "{safe_name}"
      - "--gpu-memory-utilization"
      - "{gpu_util}"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    shm_size: '8gb'
"""

    # Generate LiteLLM gateway service and link dependencies
    dependencies = "\n".join([f"      - vllm-{sanitize_name(m)}" for m in models])
    dependencies += "\n      - db"
    
    compose_yaml += f"""
  db:
    image: postgres:16-alpine
    container_name: litellm-db
    environment:
      POSTGRES_USER: llmproxy
      POSTGRES_PASSWORD: dbpassword9090
      POSTGRES_DB: litellm
    volumes:
      - postgres_data:/var/lib/postgresql/data

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: litellm
    ports:
      - "4000:4000"
    volumes:
      - ./litellm_config.yaml:/app/config.yaml
    environment:
      DATABASE_URL: "postgresql://llmproxy:dbpassword9090@db:5432/litellm"
      LITELLM_MASTER_KEY: "sk-1234"
      LITELLM_SALT_KEY: "sk-1234"
    command: [ "--config", "/app/config.yaml" ]
    depends_on:
{dependencies}

volumes:
  postgres_data:
"""

    with open("docker-compose.yml", "w") as f:
        f.write(compose_yaml)
    print("✅ Generated: docker-compose.yml")
    print("\n🎉 Configuration generation complete. You can now run: docker-compose up -d")

if __name__ == "__main__":
    main_dir = "./model_files"
    
    # For testing the script without downloading, you can create dummy folders:
    #os.makedirs("./model_files/gemma-4", exist_ok=True)
    #os.makedirs("./model_files/llama-3", exist_ok=True)
    
    generate_configs(main_dir)
