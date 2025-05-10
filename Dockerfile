# Use a lightweight official Python image
FROM python:3.12-slim


# Set the working directory inside the container
WORKDIR /app

# Combined system dependencies installation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    openssh-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /bin/uv

COPY pyproject.toml uv.lock .python-version /app/

# Install the dependencies
RUN uv sync --frozen --no-cache

RUN uv run playwright install-deps

# Copy the rest of your application code
COPY . .
