# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Copy project files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry
ENV POETRY_HTTP_TIMEOUT=120

# Install dependencies with retries
RUN poetry config virtualenvs.create false \
    && (poetry install --no-interaction --no-ansi --no-root || \
        poetry install --no-interaction --no-ansi --no-root || \
        poetry install --no-interaction --no-ansi --no-root)

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
