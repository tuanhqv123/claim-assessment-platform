# Backend: FastAPI claim-assessment agent (api.py) + local fastembed embeddings.
# Python 3.12 (stable wheels for onnxruntime/fastembed/tokenizers on linux).
FROM python:3.12-slim

# poppler-utils -> pdftoppm, needed to OCR PDF policy documents (src/ocr/document_text.py)
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching).
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# NOTE: the embedding model (BAAI/bge-small-en-v1.5, ~80MB) is NOT baked into the
# image — fastembed downloads it lazily on first use at runtime. Mount a volume on
# the HuggingFace cache if you want it to persist across container restarts.

# Application code. (.dockerignore keeps web/, .venv/, node_modules, etc. out.)
COPY api.py run_agent.py ./
COPY src ./src
COPY config ./config
COPY data ./data

# Writable scratch dir for upload temp files.
RUN mkdir -p uploads

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
