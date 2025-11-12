"""Excel to RPA request conversion utilities."""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Union


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
    
    # Prepare data: convert to string, strip, and filter out empty values
    df[dt_col] = df[dt_col].astype(str).str.strip()
    df[nota_fiscal_col] = df[nota_fiscal_col].astype(str).str.strip()
    
    # Filter rows that have both DT and NOTA FISCAL values
    df_filtered = df[
        (df[dt_col] != "") & 
        (df[dt_col].notna()) & 
        (df[nota_fiscal_col] != "") & 
        (df[nota_fiscal_col].notna())
    ]
    
    if len(df_filtered) == 0:
        raise ValueError("No rows with both DT and NOTA FISCAL values found")
    
    # Group by DT and collect unique notas fiscais for each DT
    dt_list = []
    for dt_id, group in df_filtered.groupby(dt_col):
        # Get unique notas fiscais for this DT, preserving order
        notas_fiscais = group[nota_fiscal_col].drop_duplicates(keep='first').tolist()
        dt_list.append({
            "dt_id": dt_id,
            "notas_fiscais": notas_fiscais
        })
    
    # Return exact dict that matches rpa-api model
    # rpa_request must be a Dict[str, Any] per API validation, so wrap array in dict
    return {
        "rpa_key_id": "ecargo_pod_download",
        "rpa_request": {
            "dt_list": dt_list
        }
    }


