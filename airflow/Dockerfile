FROM apache/airflow:2.9.3

# Install system dependencies for OCR and image processing
USER root
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install required Python dependencies
USER airflow
RUN pip install --no-cache-dir \
    "apache-airflow-providers-microsoft-winrm<3.0.0" \
    pandas \
    openpyxl \
    xlrd \
    fastapi \
    uvicorn \
    httpx \
    boto3 \
    pypdf \
    pymupdf \
    pdfplumber \
    pytesseract \
    pillow \
    fpdf2 \
    pdf2image \
    numpy \
    opencv-python \
    paddleocr \
    easyocr

# Add src directory to Python path
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow/src"

# Copy startup script
COPY --chown=airflow:root scripts/start-with-api.sh /start-with-api.sh
RUN chmod +x /start-with-api.sh


