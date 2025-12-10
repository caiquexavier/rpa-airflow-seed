"""Excel to RPA request conversion utilities."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd


def xls_to_rpa_request(xlsx_path: Union[str, Path]) -> Dict[str, Any]:
    """Convert XLSX file to RPA request payload by extracting NOTA FISCAL values."""
    src_path = Path(xlsx_path)
    
    if not src_path.exists():
        # Provide detailed error message with diagnostics
        error_msg = f"Source file not found: {src_path}\n"
        error_msg += f"  Absolute path: {src_path.resolve()}\n"
        
        # Check if parent directory exists
        parent_dir = src_path.parent
        if not parent_dir.exists():
            error_msg += f"  Parent directory does not exist: {parent_dir}\n"
        else:
            error_msg += f"  Parent directory exists: {parent_dir}\n"
            # List files in parent directory if accessible
            try:
                files = list(parent_dir.iterdir())
                if files:
                    error_msg += f"  Files in parent directory: {[f.name for f in files[:10]]}\n"
                else:
                    error_msg += f"  Parent directory is empty\n"
            except PermissionError:
                error_msg += f"  Cannot list files in parent directory (permission denied)\n"
        
        raise FileNotFoundError(error_msg)
    
    # Read first sheet of Excel file
    try:
        df = pd.read_excel(src_path, sheet_name=0)
    except Exception as e:
        raise ValueError(f"Failed to read Excel file {src_path}: {e}")
    
    # Find NOTA FISCAL column (case-insensitive, trim header)
    nota_fiscal_col = None
    for col in df.columns:
        if col.strip().upper() == "NOTA FISCAL":
            nota_fiscal_col = col
            break
    
    if nota_fiscal_col is None:
        raise ValueError("NOTA FISCAL column not found")
    
    # Find DT column (case-insensitive, trim header)
    dt_col = None
    for col in df.columns:
        if col.strip().upper() == "DT":
            dt_col = col
            break
    
    if dt_col is None:
        raise ValueError("DT column not found")
    
    # Find STATUS RPA column
    status_col = None
    for col in df.columns:
        if col.strip().upper() == "STATUS RPA":
            status_col = col
            break
    
    if status_col is None:
        raise ValueError("STATUS RPA column not found")
    
    # Find CD column (case-insensitive, trim header) - renamed to centro_distribuicao
    cd_col = None
    for col in df.columns:
        if col.strip().upper() == "CD":
            cd_col = col
            break
    
    # Prepare data: convert to string, strip, and filter out empty values
    df[dt_col] = df[dt_col].astype(str).str.strip()
    df[nota_fiscal_col] = df[nota_fiscal_col].astype(str).str.strip()
    df[status_col] = df[status_col].astype(str).str.strip().str.upper()
    if cd_col:
        df[cd_col] = df[cd_col].astype(str).str.strip()
    
    # Filter rows that have both DT and NOTA FISCAL values
    df_filtered = df[
        (df[dt_col] != "") & 
        (df[dt_col].notna()) & 
        (df[nota_fiscal_col] != "") & 
        (df[nota_fiscal_col].notna()) &
        # Only rows marked to be processed by RPA should be considered
        (df[status_col] == "PROCESSAR")
    ]
    
    if len(df_filtered) == 0:
        raise ValueError("No rows with both DT and NOTA FISCAL values found")
    
    # Group by DT and collect unique notas fiscais (NOTA FISCAL) for each DT
    doc_transportes_list = []
    for doc_transportes, group in df_filtered.groupby(dt_col):
        # Get unique notas fiscais for this DT, preserving order
        nf_e_values = group[nota_fiscal_col].drop_duplicates(keep="first").tolist()
        if not nf_e_values:
            continue
        
        # Get centro_distribuicao from CD column (should be same for all rows with same DT)
        centro_distribuicao = None
        if cd_col:
            cd_values = group[cd_col].dropna().unique()
            if len(cd_values) > 0:
                centro_distribuicao = str(cd_values[0]).strip()
                if centro_distribuicao == "":
                    centro_distribuicao = None
        
        doc_entry = {
            "doc_transportes": doc_transportes,
            # Keep full list of NOTA FISCAL values for this DT
            "nf_e": nf_e_values,
        }
        
        # Add centro_distribuicao if available
        if centro_distribuicao:
            doc_entry["centro_distribuicao"] = centro_distribuicao
        
        doc_transportes_list.append(doc_entry)
    
    # Return RPA request data (not SAGA structure)
    # Uses 'data' field (rpa_request_object was replaced)
    return {
        "rpa_key_id": "rpa_protocolo_devolucao",
        "data": {
            "doc_transportes_list": doc_transportes_list
        }
    }


