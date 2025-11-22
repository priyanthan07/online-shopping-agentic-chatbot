FROM python:3.12-slim

WORKDIR /app

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using UV (will use Python 3.12)
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY data/ ./data/
COPY mcp_server/ ./mcp_server/
COPY app.py ./

# Create necessary directories
RUN mkdir -p logs chroma_db

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit app by default
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]