"""PDF field map model - defines field mappings for GPT extraction."""
from typing import Dict


# Field map for transport document extraction
# Maps field names to empty descriptions (field names are self-descriptive)
PDF_FIELD_MAP: Dict[str, str] = {
    "razao_social_transportadora": "",
    "cnpj_transportadora": "",
    "endereco_transportadora": "",
    "uf_transportadora": "",
    "municipio_transportadora": "",
    "razao_destinatario": "",
    "cnpj_destinatario": "",
    "endereco_destinatario": "",
    "uf_destinatario": "",
    "municipio_destinatario": "",
    "centro": "",
    "valor_total_da_nf": "",
    "valor_para_seguros": "",
    "valor_desconto": "",
    "valor_cobranca": "",
    "outras_despesas": "",
    "doc_transportes": "Documento de Transporte (DT) - Transport document number, usually 8-15 digits, may appear as 'DT', 'Documento de Transporte', 'Nº DT', or similar labels",
    "fatura": "",
    "remessa": "",
    "doc_externo_tms": "",
    "quantidade": "",
    "especie": "",
    "peso_bruto": "",
    "data_emissao": "",
    "data_entrega": "",
    "nome": "",
    "rg": "",
    "telefone_contato": "",
    "nf_e": "Nota Fiscal Eletrônica (NF-e) - Electronic invoice number, CRITICAL field, typically 5-15 digits, search entire document including headers, footers, QR codes, barcodes. Look for labels like 'NF-e', 'NFE', 'Nota Fiscal', 'Nº NF-e', 'Número NF-e'. Extract ALL digits exactly as shown.",
    "serie": "",
    "observacoes": ""
}


def get_pdf_field_map() -> Dict[str, str]:
    """
    Get the PDF field map for GPT extraction.
    
    Returns:
        Dictionary mapping field names to descriptions/instructions
    """
    return PDF_FIELD_MAP.copy()

