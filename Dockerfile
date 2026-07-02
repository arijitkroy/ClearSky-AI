# Stage 1: Build the static Next.js frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
# Inject empty API URL to compile relative fetch paths for single-host hosting
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# Stage 2: Final runner container
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for compiling python packages if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

COPY . .

# Copy built frontend static files from Stage 1
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Make run script executable
RUN chmod +x run.sh

ENV PYTHONPATH=/app

EXPOSE 7860

CMD ["./run.sh"]
