FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for compiled wheels (e.g. scikit-learn).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY fixops/ ./fixops/
COPY knowledge_base/ ./knowledge_base/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN pip install --no-cache-dir ".[server,local]"

RUN groupadd -r fixops && useradd -r -g fixops fixops
USER fixops

EXPOSE 8000

CMD ["fixops", "server"]
