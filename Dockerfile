# Packagebot Dockerfile
# Multi-ecosystem support: Python, Node.js, Go

FROM python:3.11-slim-bookworm

LABEL maintainer="packagebot"
LABEL description="Automated Dependabot alert remediation system"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Poetry settings
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

# Go settings
ENV GOROOT="/usr/local/go"
ENV GOPATH="/go"
ENV PATH="${GOPATH}/bin:${GOROOT}/bin:${POETRY_HOME}/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install npm package managers (yarn, pnpm)
RUN npm install -g yarn pnpm

# Install Go 1.22
ARG GO_VERSION=1.22.5
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" | tar -C /usr/local -xz

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx 2>/dev/null || true

# Create app user for security
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN poetry install --no-root --no-dev 2>/dev/null || poetry install --no-root

# Copy application code
COPY . .

# Install the application
RUN poetry install --no-dev 2>/dev/null || poetry install

# Create directories for workspace and logs
RUN mkdir -p /app/workspace /app/logs /app/dependabot-remediation-plan \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import temporalio; print('healthy')" || exit 1

# Default command - start the Temporal worker
CMD ["python", "worker.py"]
