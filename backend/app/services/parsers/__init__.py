"""
Provider-specific parsers
"""
from .uatl_parser import parse_uatl_pdf
from .umtn_parser import parse_umtn_excel

def get_parser(provider_code: str):
    """
    Get parser function for provider

    Args:
        provider_code: Provider code ('UATL', 'UMTN', etc.)

    Returns:
        Parser function

    Raises:
        ValueError: If no parser for provider
    """
    parsers = {
        'UATL': parse_uatl_pdf,
        'UMTN': parse_umtn_excel,
    }

    if provider_code not in parsers:
        raise ValueError(f"No parser for provider: {provider_code}. Available: {list(parsers.keys())}")

    return parsers[provider_code]


__all__ = ['parse_uatl_pdf', 'parse_umtn_excel', 'get_parser']
