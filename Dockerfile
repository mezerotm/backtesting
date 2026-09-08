# Finance Dashboard - backend runtime image.
#
# Serves the FastAPI backend AND the built Vue frontend (public/) on the same
# origin on port 8000 inside the container. Portainer/NPM proxy to this port.
#
# The frontend is built ON THE HOST with `make build-frontend` (which is the
# project's canonical production build, reusing existing node_modules) and
# copied into the image as public/. This avoids re-running npm ci / vue-tsc
# inside the build, which is slow and non-deterministic.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ENV=production \
    VITE_API_URL=

WORKDIR /app

# Build toolchain + TA-Lib C library (bundled .deb) needed by `pip install ta-lib`.
# The .deb installs libta-lib.so (hyphen); pip's ta-lib looks for libta_lib.so
# (underscore), so symlink it and point TA_INCLUDE_PATH/TA_LIBRARY_PATH at it.
COPY libs/ta-lib_0.6.4_amd64.deb /tmp/ta-lib.deb
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ /tmp/ta-lib.deb && \
    rm -f /tmp/ta-lib.deb && \
    ln -sf /usr/lib/libta-lib.so /usr/lib/libta_lib.so && \
    ldconfig && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# TA-Lib build hints for the Python wheel
ENV TA_INCLUDE_PATH=/usr/include/ta-lib \
    TA_LIBRARY_PATH=/usr/lib

# Python dependencies below (layer cached; only re-installs when requirements change).
# NB: the repo pins ta-lib==0.6.3, which does NOT compile against numpy>=2. We
# install everything else from requirements.txt and use the modern TA-Lib==0.7.1
# binding (imports as `talib`) which supports numpy 2 + the bundled C lib 0.6.4.
COPY requirements.txt .
RUN sed '/^ta-lib==/d' requirements.txt | pip install --no-cache-dir -r /dev/stdin && \
    pip install --no-cache-dir "TA-Lib==0.7.1"

# Application source + built frontend. Excludes heavy/volatile dirs.
COPY server ./server
COPY config ./config
COPY scripts ./scripts
COPY workflows ./workflows
COPY strategies ./strategies
COPY libs ./libs
COPY public ./public
COPY data ./data
COPY *.py ./

# Run the FastAPI app directly with uvicorn (module path resolved from /app).
# Serve the API + built frontend together on :8000.
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "error"]