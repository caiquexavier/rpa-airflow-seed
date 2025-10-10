"""Excel to RPA request conversion utilities."""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Union


def xls_to_rpa_request(xlsx_path: Union[str, Path]) -> Dict[str, Any]:
    """Convert XLSX file to RPA request payload by extracting NOTA FISCAL values."""
    src_path = Path(xlsx_path)
    
    if not src_path.exists():
        raise FileNotFoundError(f"Source file not found: {src_path}")
    
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
    
    # Extract values, drop blanks/NaN, dedupe preserving order, coerce to str().strip()
    values = df[nota_fiscal_col].dropna().astype(str).str.strip()
    values = values[values != ""]  # Remove empty strings
    values = values.drop_duplicates(keep='first')  # Dedupe preserving order
    
    if len(values) == 0:
        raise ValueError("No NOTA FISCAL values found")
    
    # Convert to list of strings
    notas_fiscais = values.tolist()
    
    # Return exact dict that matches rpa-api model
    return {
        "rpa_id": "ecargo_pod_download",
        "rpa_request": {
            "notas_fiscais": notas_fiscais
        }
    }


