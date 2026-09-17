# Finance Dashboard - backend runtime image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app ENV=production VITE_API_URL=
WORKDIR /app

COPY libs/ta-lib_0.6.4_amd64.deb /tmp/ta-lib.deb
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ /tmp/ta-lib.deb && \
    rm -f /tmp/ta-lib.deb && \
    ln -sf /usr/lib/libta-lib.so /usr/lib/libta_lib.so && \
    ldconfig && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV TA_INCLUDE_PATH=/usr/include/ta-lib TA_LIBRARY_PATH=/usr/lib

COPY requirements.txt .
RUN pip install --upgrade pip && \
    sed '/^ta-lib==/d' requirements.txt | pip install --no-cache-dir -r /dev/stdin && \
    pip install --no-cache-dir "TA-Lib==0.7.1"

COPY server ./server
COPY config ./config
COPY scripts ./scripts
COPY workflows ./workflows
COPY strategies ./strategies
COPY public ./public
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "error"]