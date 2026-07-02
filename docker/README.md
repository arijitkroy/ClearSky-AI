# ClearSky AI Docker Deployments

This directory describes how the containerized microservices are organized for production orchestration.

## Structure
* Root `docker-compose.yml`: Coordinates the launching, volumes, and networking of the three containers.
* `backend/Dockerfile`: Multi-stage Python 3.12-slim container running Uvicorn and FastAPI.
* `frontend/Dockerfile`: Multi-stage Node 20-alpine container running Next.js build and runner steps.
* `simulator/`: Reuses the backend python environment to run in the background.

## Commands
To boot the full multi-service cluster:
```bash
docker-compose up --build
```
This launches:
1. `backend` service (FastAPI) on port 8000.
2. `frontend` service (Next.js) on port 3000.
3. `simulator` service running in background.
