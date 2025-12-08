"""Centro access credentials mapping for Robot Framework variables.

This file provides access information (CNPJ, usuario, senha) for different centro values.
The centro value comes from saga data or fallback defaults.
"""

# Centro access credentials mapping
CENTRO_ACCESS = {
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


def get_centro_access(centro: str):
    """
    Get access credentials for a given centro value.
    
    Args:
        centro: Centro identifier (e.g., "3202", "5183", "3031", "5197")
        
    Returns:
        Dictionary with CNPJ, usuario, and senha, or None if centro not found
    """
    return CENTRO_ACCESS.get(str(centro))


def get_centro_cnpj(centro: str):
    """Get CNPJ for a given centro."""
    access = get_centro_access(centro)
    return access.get("CNPJ") if access else None


def get_centro_usuario(centro: str):
    """Get usuario for a given centro."""
    access = get_centro_access(centro)
    return access.get("usuario") if access else None


def get_centro_senha(centro: str):
    """Get senha for a given centro."""
    access = get_centro_access(centro)
    return access.get("senha") if access else None

