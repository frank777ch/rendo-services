FROM python:3.12-slim

# poppler-utils da pdftotext (extrae texto de los PDF, sin OCR)
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# La API no necesita Playwright; se instala solo httpx/fastapi para mantener la imagen liviana.
RUN pip install --no-cache-dir httpx python-dotenv "fastapi>=0.115" "uvicorn[standard]>=0.30"

COPY rendo/ ./rendo/
EXPOSE 8000
CMD ["uvicorn", "rendo.api:app", "--host", "0.0.0.0", "--port", "8000"]
