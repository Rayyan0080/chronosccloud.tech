"""
Secret Masking Utility

Provides functions to mask sensitive environment variables and API keys in logs.
"""

import os
import re
from typing import Any, Dict, Optional


# List of environment variable names that contain secrets
SECRET_ENV_VARS = [
    "API_KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "DSN",
    "PRIVATE_KEY",
    "ACCESS_KEY",
    "CREDENTIAL",
]


def mask_secret(value: str, show_chars: int = 4) -> str:
    """
    Mask a secret value, showing only first few characters.
    
    Args:
        value: Secret value to mask
        show_chars: Number of characters to show at the start (default: 4)
        
    Returns:
        Masked string (e.g., "sk-...xxxx" or "****" if too short)
    """
    if not value:
        return "****"
    
    if len(value) <= show_chars:
        return "*" * len(value)
    
    return value[:show_chars] + "..." + "*" * min(8, len(value) - show_chars)


def mask_env_var(env_var_name: str) -> str:
    """
    Check if an environment variable name contains secrets and mask its value.
    
    Args:
        env_var_name: Name of the environment variable
        
    Returns:
        Masked value if it's a secret, original value otherwise
    """
    value = os.getenv(env_var_name)
    if not value:
        return "not set"
    
    # Check if variable name suggests it's a secret
    env_var_upper = env_var_name.upper()
    for secret_pattern in SECRET_ENV_VARS:
        if secret_pattern in env_var_upper:
            return mask_secret(value)
    
    return value


def mask_dict_secrets(data: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
    """
    Recursively mask secrets in a dictionary.
    
    Args:
        data: Dictionary that may contain secrets
        max_depth: Maximum recursion depth (default: 3)
        
    Returns:
        Dictionary with secrets masked
    """
    if max_depth <= 0:
        return {"[REDACTED: max depth reached]": None}
    
    masked = {}
    for key, value in data.items():
        key_upper = str(key).upper()
        
        # Check if key suggests it's a secret
        is_secret = any(pattern in key_upper for pattern in SECRET_ENV_VARS)
        
        if is_secret and isinstance(value, str):
            masked[key] = mask_secret(value)
        elif isinstance(value, dict):
            masked[key] = mask_dict_secrets(value, max_depth - 1)
        elif isinstance(value, list) and len(value) > 10:
            # Large lists might contain secrets - redact
            masked[key] = f"[REDACTED: {len(value)} items]"
        else:
            masked[key] = value
    
    return masked


def mask_string_secrets(text: str) -> str:
    """
    Mask secrets in a string (e.g., log messages).
    
    Args:
        text: Text that may contain secrets
        
    Returns:
        Text with secrets masked
    """
    # Pattern to match common secret formats
    patterns = [
        (r'(api[_-]?key["\s:=]+)([a-zA-Z0-9_-]{10,})', r'\1[MASKED]'),
        (r'(secret["\s:=]+)([a-zA-Z0-9_-]{10,})', r'\1[MASKED]'),
        (r'(password["\s:=]+)([^\s"\'<>]+)', r'\1[MASKED]'),
        (r'(token["\s:=]+)([a-zA-Z0-9_-]{10,})', r'\1[MASKED]'),
    ]
    
    masked_text = text
    for pattern, replacement in patterns:
        masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)
    
    return masked_text

