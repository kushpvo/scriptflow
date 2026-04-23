FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DATA_DIR=/data
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

# Pre-fetch all supported Python versions so no internet access needed at runtime
RUN uv python install 3.10 3.11 3.12 3.13 3.14

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./
RUN uv venv --python 3.12 && uv sync --frozen --no-dev

COPY app/ ./app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

CMD ["/app/.venv/bin/python", "-c", "from app.database import init_db; init_db(); import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=8000)"]