"""
Utilities Module

Other common functions and utilities.
Used by the Hive Engine Tokens Snapshot tool.

Created by https://peakd.com/@gadrian using "vibe" coding in June 2025.
"""

# Validation utilities
def validate_username(username):
    """
    Validate Hive username according to rules:
    - Must be lowercase (should be automatically)
    - Start with a letter
    - Only letters, numbers, dashes, and dots
    - Length between 3 and 16 characters
    - Dashes and dots cannot be consecutive or at beginning/end
    """
    if not username:
        return False, "Username cannot be empty"
    
    # Check length
    if len(username) < 3 or len(username) > 16:
        return False, "Username must be between 3 and 16 characters"
    
    # Check if lowercase
    if username != username.lower():
        return False, "Username must be lowercase"
    
    # Check if starts with letter
    if not username[0].isalpha():
        return False, "Username must start with a letter"
    
    # Check if ends with dash or dot
    if username[-1] in '-.':
        return False, "Username cannot end with dash or dot"
    
    # Check allowed characters
    allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-.')
    if not all(c in allowed_chars for c in username):
        return False, "Username can only contain letters, numbers, dashes, and dots"
    
    # Check for consecutive dashes/dots
    for i in range(len(username) - 1):
        if username[i] in '-.' and username[i + 1] in '-.':
            return False, "Username cannot have consecutive dashes or dots"
    
    return True, "Valid username"

def validate_token(token, valid_token_symbols):
    """
    Validate if a token exists in Hive Engine
    
    Args:
        token: Token symbol to validate
        valid_token_symbols: Set of valid token symbols
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not token:
        return False, "Token cannot be empty"
    
    if token not in valid_token_symbols:
        return False, f"Token '{token}' is not found in Hive Engine token list"
    
    return True, "Valid token"

