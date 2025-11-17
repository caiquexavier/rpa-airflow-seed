FROM apache/airflow:2.9.3

# Install required dependencies
USER airflow
RUN pip install "apache-airflow-providers-microsoft-winrm<3.0.0" pandas openpyxl requests xlrd fastapi uvicorn httpx boto3 pypdf

# Add src directory to Python path
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow/src"

# Copy startup script
COPY --chown=airflow:root scripts/start-with-api.sh /start-with-api.sh
RUN chmod +x /start-with-api.sh


