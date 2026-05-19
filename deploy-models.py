#!/usr/bin/python3
import os
import re
import yaml
import git
from pathlib import Path

def sanitize_name(name):
    """
    Converts folder names into valid, lowercase Docker service names.
    (e.g., 'Meta-Llama-3_8B' -> 'meta-llama-3-8b')
    """
    safe_name = re.sub(r'[^a-zA-Z0-9-]', '-', name).lower()
    return re.sub(r'-+', '-', safe_name).strip('-')

def manage_recipes_repo(repo_path="recipes"):
    repo_url = "https://github.com/vllm-project/recipes.git"
    if os.path.exists(os.path.join(repo_path, ".git")):
        print(f"🔄 Updating recipes repository in {repo_path}...")
        try:
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
        except Exception as e:
            print(f"⚠️ Failed to update recipes repo: {e}")
    else:
        print(f"📥 Cloning recipes repository to {repo_path}...")
        try:
            git.Repo.clone_from(repo_url, repo_path)
        except Exception as e:
            print(f"❌ Failed to clone recipes repo: {e}")

def get_model_args(model_folder, recipes_path="recipes"):
    # Extract model name from folder (e.g., 'google/gemma-4-31B-it' -> 'gemma-4-31B-it')
    model_name = Path(model_folder).name
    
    # Search for {model_name}.yaml in recipes/models/ and recipe-fallback/
    search_paths = [
        Path(recipes_path) / "models",
        Path("recipe-fallback")
    ]
    
    recipe_file = None
    for path in search_paths:
        if not path.exists():
            continue
        # Case-insensitive search
        for p in path.rglob("*.yaml"):
            if p.stem.lower() == model_name.lower():
                recipe_file = p
                break
        if recipe_file:
            break
            
    extra_args = []
    
    # 1. Process Recipe if found
    if recipe_file:
        print(f"📖 Found recipe for {model_name}: {recipe_file}")
        try:
            with open(recipe_file, "r") as f:
                config = yaml.safe_load(f)
                
            features = config.get("features", {})
            
            # Collect all args from features to search
            recipe_args = []
            tool_calling = features.get("tool_calling", {})
            if tool_calling:
                recipe_args.extend(tool_calling.get("args", []))
            reasoning = features.get("reasoning", {})
            if reasoning:
                recipe_args.extend(reasoning.get("args", []))

            # Filter for specific flags
            if "--tool-call-parser" in recipe_args:
                idx = recipe_args.index("--tool-call-parser")
                if idx + 1 < len(recipe_args):
                    extra_args.append("--enable-auto-tool-choice")
                    extra_args.append("--tool-call-parser")
                    extra_args.append(recipe_args[idx + 1])

            if "--reasoning-parser" in recipe_args:
                idx = recipe_args.index("--reasoning-parser")
                if idx + 1 < len(recipe_args):
                    extra_args.append("--reasoning-parser")
                    extra_args.append(recipe_args[idx + 1])
        except Exception as e:
            print(f"⚠️ Error parsing recipe {recipe_file}: {e}")

    # 2. Process Custom Config from config/ directory
    # Expects config/<Provider>/<ModelName>.yaml
    custom_config_path = Path("config") / f"{model_folder}.yaml"
    if custom_config_path.exists():
        print(f"🛠️ Found custom config for {model_folder}: {custom_config_path}")
        try:
            with open(custom_config_path, "r") as f:
                custom_cfg = yaml.safe_load(f)
                custom_extra = custom_cfg.get("extra_args", [])
                if isinstance(custom_extra, list):
                    extra_args.extend(custom_extra)
        except Exception as e:
            print(f"⚠️ Error parsing custom config {custom_config_path}: {e}")
                
    return extra_args
def generate_configs(base_dir="./model_files"):
    manage_recipes_repo()
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
    litellm_config = {
        "model_list": [],
        "litellm_settings": {
            "request_timeout": 1200,
            "use_chat_completions_url_for_anthropic_messages": True
        }
    }
    
    for model_folder in models:
        safe_name = sanitize_name(model_folder)
        litellm_config["model_list"].append({
            "model_name": safe_name,
            "litellm_params": {
                "model": f"openai/{safe_name}",
                "api_base": f"http://vllm-{safe_name}:8000/v1",
                "api_key": "sk-dummy-key"
            }
        })

    with open("litellm_config.yaml", "w") as f:
        yaml.dump(litellm_config, f, default_flow_style=False, sort_keys=False)
    print("✅ Generated: litellm_config.yaml")

    # ==========================================
    # 3. Generate docker-compose.yml
    # ==========================================
    compose_dict = {
        "services": {},
        "volumes": {
            "postgres_data": None
        }
    }
    
    # Generate vLLM services dynamically
    for i, model_folder in enumerate(models):
        safe_name = sanitize_name(model_folder)
        host_port = 8000 + i  # Increment host port starting from 8000
        
        extra_args = get_model_args(model_folder)
        
        compose_dict["services"][f"vllm-{safe_name}"] = {
            "image": "vllm/vllm-openai:latest",
            "container_name": f"vllm-{safe_name}",
            "ports": [f"{host_port}:8000"],
            "volumes": ["./model_files:/model_files"],
            "command": [
                "--model", f"/model_files/{model_folder}",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--served-model-name", safe_name,
                "--gpu-memory-utilization", str(gpu_util)
            ] + extra_args,
            "deploy": {
                "resources": {
                    "reservations": {
                        "devices": [{
                            "driver": "nvidia",
                            "count": "all",
                            "capabilities": ["gpu"]
                        }]
                    }
                }
            },
            "shm_size": "8gb"
        }

    # Add DB service
    compose_dict["services"]["db"] = {
        "image": "postgres:16-alpine",
        "container_name": "litellm-db",
        "environment": {
            "POSTGRES_USER": "llmproxy",
            "POSTGRES_PASSWORD": "dbpassword9090",
            "POSTGRES_DB": "litellm"
        },
        "volumes": ["postgres_data:/var/lib/postgresql/data"]
    }

    # Add LiteLLM service
    depends_on = [f"vllm-{sanitize_name(m)}" for m in models]
    depends_on.append("db")
    
    compose_dict["services"]["litellm"] = {
        "image": "ghcr.io/berriai/litellm:main-latest",
        "container_name": "litellm",
        "ports": ["4000:4000"],
        "volumes": ["./litellm_config.yaml:/app/config.yaml"],
        "environment": {
            "DATABASE_URL": "postgresql://llmproxy:dbpassword9090@db:5432/litellm",
            "LITELLM_MASTER_KEY": "sk-1234",
            "LITELLM_SALT_KEY": "sk-1234"
        },
        "command": ["--config", "/app/config.yaml"],
        "depends_on": depends_on
    }

    with open("docker-compose.yml", "w") as f:
        yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)
    print("✅ Generated: docker-compose.yml")
    print("\n🎉 Configuration generation complete. You can now run: docker-compose up -d")

if __name__ == "__main__":
    main_dir = "./model_files"
    
    # For testing the script without downloading, you can create dummy folders:
    #os.makedirs("./model_files/gemma-4", exist_ok=True)
    #os.makedirs("./model_files/llama-3", exist_ok=True)
    
    generate_configs(main_dir)
