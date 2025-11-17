"""Airflow DAGs initialization - adds src directory to Python path globally."""
import sys
import os

# Add src directory to path for all DAGs
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

