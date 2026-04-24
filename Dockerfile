FROM python:3.12-slim as builder

WORKDIR /app

# Install uv
RUN pip install -U pip setuptools wheel
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev


### FINAL STAGES

# API
FROM python:3.12-slim as api
WORKDIR /app

# Install uv
RUN pip install -U pip setuptools wheel uv

# Set Python path to include src and site-packages
ENV PYTHONPATH=/app/src:/app/.venv/lib/python3.12/site-packages
ENV PATH=/app/.venv/bin:$PATH

# Copy virtual environment from builder
COPY --from=builder /app/.venv/ ./.venv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src

# Re-sync to ensure everything is installed (without rebuilding)
RUN uv sync --frozen --no-dev

WORKDIR /app/src
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--proxy-headers"]

# ADMIN
FROM python:3.12-slim as admin
WORKDIR /app

# Install uv
RUN pip install -U pip setuptools wheel uv

# Set Python path to include src and site-packages
ENV PYTHONPATH=/app/src:/app/.venv/lib/python3.12/site-packages
ENV PATH=/app/.venv/bin:$PATH

# Copy virtual environment from builder
COPY --from=builder /app/.venv/ /app/.venv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src

# Re-sync to ensure everything is installed
RUN uv sync --frozen --no-dev

WORKDIR /app/src
CMD ["uvicorn", "admin.main:app", "--host", "0.0.0.0", "--proxy-headers"]

# MIGRATIONS
FROM python:3.12-slim as migrations
WORKDIR /app

# Install uv
RUN pip install -U pip setuptools wheel uv

# Set Python path to include src
ENV PYTHONPATH=/app/src:/app/.venv/lib/python3.12/site-packages
ENV PATH=/app/.venv/bin:$PATH

# Copy virtual environment from builder
COPY --from=builder /app/.venv/ /app/.venv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src

# Re-sync to ensure everything is installed
RUN uv sync --frozen --no-dev

WORKDIR /app/src
CMD ["alembic", "upgrade", "head"]
