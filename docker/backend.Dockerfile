FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY python-langgraph-temporal/pyproject.toml python-langgraph-temporal/uv.lock ./
RUN uv sync --frozen --no-dev

COPY python-langgraph-temporal/ ./

EXPOSE 8002
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002"]
