# ============================================================
# FIN SIGHT AI - Dockerfile
# Production-ready container for the Streamlit application
# ============================================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# ── System dependencies ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────────
COPY . .

# ── Create required directories ───────────────────────────────
RUN mkdir -p data/uploads data/indexes reports logs

# ── Streamlit configuration ──────────────────────────────────
COPY .streamlit/ .streamlit/ 2>/dev/null || true

# ── Expose Streamlit port ─────────────────────────────────────
EXPOSE 8501

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Environment defaults (override via docker run -e or .env) ─
ENV LLM_PROVIDER=demo \
    LOG_LEVEL=INFO \
    CHUNK_SIZE=1000 \
    CHUNK_OVERLAP=200 \
    RETRIEVAL_TOP_K=5 \
    MAX_FILE_SIZE_MB=50

# ── Non-root user for security ────────────────────────────────
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ── Entrypoint ───────────────────────────────────────────────
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
