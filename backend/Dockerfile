# --- builder ---
FROM python:3.11-slim AS builder
WORKDIR /build
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY agents/ ./agents/
COPY backend/ ./backend/
RUN pip install --no-cache-dir ./agents
RUN pip install --no-cache-dir ./backend

# --- runtime ---
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
COPY backend/ ./
RUN useradd -m app && chown -R app:app /app
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
