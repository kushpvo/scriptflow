FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DATA_DIR=/data
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /usr/bin/python3 /usr/local/bin/python

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./
RUN uv venv --python python3 && uv sync --frozen --no-dev

COPY app/ ./app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

CMD ["/app/.venv/bin/python", "-c", "from app.database import init_db; init_db(); import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=8000)"]