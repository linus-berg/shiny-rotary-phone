#!/usr/bin/python3
import os
import time
import requests
from pathlib import Path
from huggingface_hub import snapshot_download

def download_with_retry(repo_id, local_dir, max_retries=3, delay=5):
    """Downloads the model using the HF API with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"  └─ Download attempt {attempt + 1}/{max_retries}...")
            # snapshot_download natively respects the HTTP_PROXY/HTTPS_PROXY environment variables
            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir + "/" + repo_id,
                local_dir_use_symlinks=False,
                # token="YOUR_HF_TOKEN" # Uncomment and add token if the model is gated
            )
            print("  └─ ✅ Download successful!\n")
            return True
        except Exception as e:
            print(f"  └─ ❌ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"     Retrying in {delay} seconds...")
                time.sleep(delay)
    return False

def upload_with_retry(filepath, relative_path, url, headers, max_retries=3, delay=5):
    """Uploads a single file to the HTTP endpoint with retry logic."""
    for attempt in range(max_retries):
        try:
            with open(filepath, 'rb') as f:
                files_payload = {'file': (filepath.name, f)}
                data_payload = {'relative_path': relative_path}
                
                response = requests.post(
                    url,
                    headers=headers,
                    files=files_payload,
                    data=data_payload,
                    timeout=60 # Added timeout to prevent hanging connections
                )
                response.raise_for_status()
                print(f"  └─ ✅ Success (Status: {response.status_code})")
                return True
        except requests.exceptions.RequestException as e:
            print(f"  └─ ❌ Upload attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"     Retrying in {delay} seconds...")
                time.sleep(delay)
    return False

def main():
    # ==========================================
    # Configuration
    # ==========================================
    MODEL_ID = "google/gemma-4-31B-it-assistant"  
    LOCAL_DIR = "./model_files"
    PROXY_URL = "http://your-proxy-server:port"
    ENDPOINT_URL = "https://your-custom-endpoint.com/upload"
    
    CUSTOM_HEADERS = {
        "Authorization": "Bearer YOUR_SECRET_TOKEN",
        "X-Custom-Deployment-ID": "offline-node-01"
    }
    # ==========================================

    # 1. Apply Proxy settings to environment variables
    # Both the HF Python API and the requests library will automatically pick these up.
    #os.environ["HTTP_PROXY"] = PROXY_URL
    #os.environ["HTTPS_PROXY"] = PROXY_URL

    print(f"Starting API download for {MODEL_ID}...")
    print(f"Routing through proxy: {PROXY_URL}")

    # 2. Execute Download
    success = download_with_retry(MODEL_ID, LOCAL_DIR)
    if not success:
        print("❌ Fatal Error: Could not download the model after multiple attempts.")
        return

    # 3. Traverse and Upload
    print(f"Starting upload to {ENDPOINT_URL}...")
    local_path = Path(LOCAL_DIR)
    
    if not local_path.exists():
        print("❌ Error: Download directory does not exist.")
        return

    for filepath in local_path.rglob('*'):
        if filepath.is_file():
            relative_path = str(filepath.relative_to(local_path))
            print(f"Uploading {relative_path}...")
            
            upload_success = upload_with_retry(
                filepath=filepath,
                relative_path=relative_path,
                url=ENDPOINT_URL,
                headers=CUSTOM_HEADERS
            )
            
            if not upload_success:
                print(f"⚠️ Warning: Failed to upload {relative_path} completely. Continuing to next file...")

    print("\n🎉 Process finished.")

if __name__ == "__main__":
    main()
