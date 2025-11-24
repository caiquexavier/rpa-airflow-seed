"""RPA response builder from Robot Framework output."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict


def build_rpa_response(message: Dict, results_dir: Path, success: bool) -> Dict:
    """Build rpa_response with status for each nota fiscal."""
    if not success:
        return {"error": extract_error_detail_from_output(results_dir)}
    
    # Get data directly (no rpa_request wrapper) - robot receives data object with doc_transportes_list
    data = message.get('data', {})
    # Extract all nf_e values from doc_transportes_list
    notas_fiscais = []
    doc_transportes_list = data.get('doc_transportes_list', [])
    for doc_transporte_entry in doc_transportes_list:
        nf_e = doc_transporte_entry.get('nf_e', [])
        notas_fiscais.extend(nf_e)
    errors_map = _extract_errors_from_output(results_dir, notas_fiscais)
    
    return {
        "notas_fiscais": [
            {
                "nota_fiscal": str(nf),
                "status": "error",
                "error_message": errors_map[str(nf)]
            } if str(nf) in errors_map else {
                "nota_fiscal": str(nf),
                "status": "success"
            }
            for nf in notas_fiscais
        ]
    }


def extract_error_detail_from_output(results_dir: Path) -> str:
    """Extract error detail string from Robot Framework output.xml."""
    try:
        output_xml = results_dir / 'output.xml'
        if not output_xml.exists():
            return "Robot execution failed"
        
        tree = ET.parse(str(output_xml))
        root = tree.getroot()
        
        error_messages = []
        
        # Check status elements
        for status in root.iter('status'):
            if status.get('status') == 'FAIL' and (status.text and status.text.strip()):
                text = status.text.strip()
                # Check for connection errors
                if re.search(r'HTTPConnectionPool|Connection.*refused|Failed to establish', text, re.IGNORECASE):
                    return text.splitlines()[0][:300]
                # Check for timeout/locator errors
                ms_match = re.search(r"Timeout\s+(\d+)ms", text)
                locator_match = re.search(r"waiting for locator\('([^']+)'\) to be ([^\n\r]+)", text)
                if ms_match and locator_match:
                    ms = int(ms_match.group(1))
                    seconds = max(1, round(ms / 1000))
                    selector = locator_match.group(1)
                    condition = locator_match.group(2).strip()
                    return f"Element {selector} not {condition} within {seconds}s"
                error_messages.append(text.splitlines()[0][:300])
        
        # Check msg elements
        for msg in root.iter('msg'):
            if msg.get('level') == 'FAIL' and (msg.text and msg.text.strip()):
                msg_text = msg.text.strip()
                # Check for connection errors
                if re.search(r'HTTPConnectionPool|Connection.*refused|Failed to establish', msg_text, re.IGNORECASE):
                    return msg_text.splitlines()[0][:300]
                error_messages.append(msg_text.splitlines()[0][:300])
        
        # Return first error message found
        if error_messages:
            return error_messages[0]
            
    except ET.ParseError as e:
        return f"XML parsing error: {str(e)[:200]}"
    except Exception as e:
        return f"Error extracting from output.xml: {str(e)[:200]}"
    
    return "Robot execution failed"


def _extract_errors_from_output(results_dir: Path, notas_fiscais: list) -> Dict[str, str]:
    """Extract error messages mapped by nota fiscal from output.xml."""
    errors_map = {}
    try:
        output_xml = results_dir / 'output.xml'
        if not output_xml.exists():
            return errors_map
        
        tree = ET.parse(str(output_xml))
        root = tree.getroot()
        current_nf = None
        
        for msg in root.iter('msg'):
            msg_text = msg.text or ""
            
            # Track current nota fiscal
            for nf in notas_fiscais:
                nf_str = str(nf)
                if f"Processing Nota Fiscal {nf_str}" in msg_text or f"[{nf_str}] Processing" in msg_text:
                    current_nf = nf_str
            
            # Extract error if error modal detected
            if "Error modal detected" in msg_text:
                if "after search:" in msg_text:
                    error_text = msg_text.split("after search:", 1)[1].strip()
                elif ":" in msg_text:
                    error_text = msg_text.split(":", 1)[1].strip()
                else:
                    error_text = ""
                
                if current_nf and error_text:
                    errors_map[current_nf] = error_text
                    
    except Exception:
        pass
    
    return errors_map

