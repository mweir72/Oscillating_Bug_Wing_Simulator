# Use a slim Python base image
FROM python:3.10-slim AS base

# Create non-root user
RUN useradd -m appuser
USER appuser

# Set working directory
WORKDIR /app

# Copy requirements first (cache optimization)
COPY --chown=appuser:appuser requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY --chown=appuser:appuser . .

# Expose the FastAPI port
EXPOSE 8000

# Default command: start FastAPI with uvicorn
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
