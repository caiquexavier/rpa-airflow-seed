"""Centro distribuição access credentials mapping for Robot Framework variables.

This file provides access information (CNPJ, usuario, senha) for different centro_distribuicao values.
The centro_distribuicao value comes from saga data or fallback defaults.
"""

# Centro distribuição access credentials mapping
CENTRO_DISTRIBUICAO_ACCESS = {
    "3202": {
        "CNPJ": "61.068.276/0007-91",
        "usuario": "ingrid.santos-PE",
        "senha": "cmacgm#24#24"
    },
    "5183": {
        "CNPJ": "61.068.276/0159-85",
        "usuario": "ingrid.santos-PE",
        "senha": "cmacgm#24#24"
    },
    "3031": {
        "CNPJ": "61.068.276/0307-80",
        "usuario": "ingrid.santos-SPS",
        "senha": "cmacgm#24#24"
    },
    "5197": {
        "CNPJ": "61.068.276/0028-16",
        "usuario": "ingrid.santos-SPS",
        "senha": "cmacgm#24#24"
    }
}


def get_centro_distribuicao_access(centro_distribuicao: str):
    """
    Get access credentials for a given centro_distribuicao value.
    
    Args:
        centro_distribuicao: Centro distribuição identifier (e.g., "3202", "5183", "3031", "5197")
        
    Returns:
        Dictionary with CNPJ, usuario, and senha, or None if centro_distribuicao not found
    """
    return CENTRO_DISTRIBUICAO_ACCESS.get(str(centro_distribuicao))


def get_centro_distribuicao_cnpj(centro_distribuicao: str):
    """Get CNPJ for a given centro_distribuicao."""
    access = get_centro_distribuicao_access(centro_distribuicao)
    return access.get("CNPJ") if access else None


def get_centro_distribuicao_usuario(centro_distribuicao: str):
    """Get usuario for a given centro_distribuicao."""
    access = get_centro_distribuicao_access(centro_distribuicao)
    return access.get("usuario") if access else None


def get_centro_distribuicao_senha(centro_distribuicao: str):
    """Get senha for a given centro_distribuicao."""
    access = get_centro_distribuicao_access(centro_distribuicao)
    return access.get("senha") if access else None

