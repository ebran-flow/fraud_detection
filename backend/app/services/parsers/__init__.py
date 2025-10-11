"""
Provider-specific parsers
"""
import os
from .uatl_parser import parse_uatl_pdf
from .uatl_csv_parser import parse_uatl_csv
from .umtn_parser import parse_umtn_excel

def get_parser(provider_code: str, file_path: str = None):
    """
    Get parser function for provider and file type

    Args:
        provider_code: Provider code ('UATL', 'UMTN', etc.)
        file_path: Path to file (used to determine file type)

    Returns:
        Parser function

    Raises:
        ValueError: If no parser for provider/file type
    """
    # Get file extension
    ext = os.path.splitext(file_path)[1].lower() if file_path else ''

    # Provider-specific parsers based on file type
    if provider_code == 'UATL':
        if ext == '.csv':
            return parse_uatl_csv
        else:  # .pdf or default
            return parse_uatl_pdf
    elif provider_code == 'UMTN':
        return parse_umtn_excel
    else:
        raise ValueError(f"No parser for provider: {provider_code}")


__all__ = ['parse_uatl_pdf', 'parse_uatl_csv', 'parse_umtn_excel', 'get_parser']
