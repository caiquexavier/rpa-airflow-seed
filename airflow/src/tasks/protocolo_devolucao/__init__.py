"""Protocolo Devolução tasks module."""

from .convert_xls_to_json import convert_xls_to_json_task
from .upload_nf_files_to_s3 import upload_nf_files_to_s3_task
from .complete_saga import complete_saga_task
from .generate_protocolo_pdf import generate_protocolo_pdf_task
from .categorize_protocolo_devolucao import categorize_protocolo_devolucao_task

__all__ = [
    "convert_xls_to_json_task",
    "upload_nf_files_to_s3_task",
    "complete_saga_task",
    "generate_protocolo_pdf_task",
    "categorize_protocolo_devolucao_task",
]

