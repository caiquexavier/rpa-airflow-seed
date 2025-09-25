FROM apache/airflow:2.9.3

# Install WinRM provider compatible with Airflow 2.9.x
USER airflow
RUN pip install "apache-airflow-providers-microsoft-winrm<3.0.0"


