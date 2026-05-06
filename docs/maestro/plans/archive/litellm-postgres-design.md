# Design Document: PostgreSQL Persistence for LiteLLM

This design outlines the addition of a PostgreSQL database to the `shiny-rotary-phone` deployment to enable full LiteLLM functionality.

## Requirements
- Persistent storage for LiteLLM data (virtual keys, usage logs, model configurations).
- Automatic configuration via the `deploy-models.py` script.
- Correct service dependency mapping in `docker-compose.yml`.

## Proposed Architecture
- **Database**: PostgreSQL 16 Alpine running as a sidecar service named `db`.
- **Persistence**: Docker named volume `postgres_data` mounted to `/var/lib/postgresql/data`.
- **Connectivity**: LiteLLM container connects via `DATABASE_URL`.
- **Security**: Basic credentials provided via environment variables (Master Key and Salt Key).

## Deployment Script Changes
- Update `deploy-models.py` to:
    - Generate the `db` service definition.
    - Inject database environment variables into the `litellm` service.
    - Ensure `litellm` depends on `db`.
    - Include the top-level `volumes` declaration.
