FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	VIRTUAL_ENV=/opt/venv

WORKDIR /app

# Builder stage installs dependencies into a reusable virtualenv
RUN python -m venv ${VIRTUAL_ENV} && \
	apt-get update && \
	apt-get install -y --no-install-recommends build-essential curl && \
	rm -rf /var/lib/apt/lists/*

ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY requirements.txt ./
RUN pip install --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONPATH=/app \
	PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update && \
	apt-get install -y --no-install-recommends curl && \
	rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
