FROM python:3.12-slim

WORKDIR /app

# Install uv (small + fast dependency manager)
RUN pip install --no-cache-dir uv

# Copy dependency manifests first for better Docker layer caching
COPY pyproject.toml uv.lock README.md ./

# Install runtime deps into the container (system python)
RUN uv sync --frozen --no-dev

# Copy app code
COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

