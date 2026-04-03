# agents/admissions/utils.py

import os
import re

def sanitize_key(name: str) -> str:
    """Sanitizes file names to be used as graph node keys."""
    # Remove extension, lower case, replace non-alphanumeric with underscore
    name = os.path.splitext(name)[0]
    # Replace common separators with space then sanitize
    name = name.replace("&", " and ").replace(",", " ")
    key = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
    # Collapse multiple underscores
    key = re.sub(r'_+', '_', key)
    return key.strip('_')
