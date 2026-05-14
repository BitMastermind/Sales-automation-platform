# --- builder ---
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --prefix=/install .

# --- runtime ---
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN useradd -m app && chown -R app:app /app
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
