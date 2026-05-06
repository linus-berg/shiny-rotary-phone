# Design Document: Command Line Interface for Model Download Script

This design outlines the transition of `download-models.py` from a hardcoded configuration to a dynamic command-line interface.

## Requirements
- Accept `model_id` as a required command-line argument.
- Ensure only files from the requested model are uploaded to the listener endpoint.
- Maintain existing retry logic and proxy support.

## Proposed Changes

### Argument Parsing
Introduce the `argparse` library to handle user input.
- New Argument: `model_id` (String, Required).

### Target Path Logic
- **Download**: Continue using `LOCAL_DIR / repo_id`.
- **Upload**: Instead of scanning all of `LOCAL_DIR`, explicitly scan `LOCAL_DIR / MODEL_ID`. This ensures that even if other models exist in `model_files/`, they are ignored during the current run.

### Path Safety
- Verify that `LOCAL_DIR / MODEL_ID` exists before attempting traversal.
- Ensure `relative_to(LOCAL_DIR)` is used to maintain the namespace/model structure for the server.
