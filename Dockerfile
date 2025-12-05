# Use a slim Python base image
FROM python:3.10-slim AS base

# Set a non-root user for security
RUN useradd -m appuser
USER appuser

# Set working directory
WORKDIR /app

# Copy requirement file first (better caching)
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies safely
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY --chown=appuser:appuser . .

# Default command (can be overridden)
CMD ["python", "run_simulation.py"]
