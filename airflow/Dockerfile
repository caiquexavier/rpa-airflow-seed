FROM apache/airflow:2.9.3

# Install required dependencies
USER airflow
RUN pip install apache-airflow-providers-microsoft-winrm<3.0.0 pandas openpyxl requests xlrd

# Add src directory to Python path
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow/src"


