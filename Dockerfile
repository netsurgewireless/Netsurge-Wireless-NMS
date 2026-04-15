FROM python:3.12-slim

LABEL maintainer="Netsurge Wireless <support@netsurgewireless.com>"
LABEL description="Netsurge Wireless Network Monitoring System"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsnmp-dev \
    snmp \
    ipmitool \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/ai_cache /app/data

EXPOSE 8080

ENV PORT=8080 \
    HOST=0.0.0.0

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

CMD ["python", "-m", "src.server"]
