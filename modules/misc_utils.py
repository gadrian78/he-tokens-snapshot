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

# utils for snapshots

def get_snapshot_types_for_date(date_obj):
    """Determine which snapshot types should be taken for a given date"""
    snapshot_types = ['daily']  # Always take daily snapshots
    
    # Weekly snapshots on Mondays (weekday 0)
    if date_obj.weekday() == 0:
        snapshot_types.append('weekly')
    
    # Monthly snapshots on 1st of month
    if date_obj.day == 1:
        snapshot_types.append('monthly')
    
    # Quarterly snapshots (1st day of quarters: Jan, Apr, Jul, Oct)
    if date_obj.day == 1 and date_obj.month in [1, 4, 7, 10]:
        snapshot_types.append('quarterly')
    
    # Yearly snapshots on January 1st
    if date_obj.day == 1 and date_obj.month == 1:
        snapshot_types.append('yearly')
    
    return snapshot_types

def generate_snapshot_filename(snapshot_type, account, date_obj):
    """Generate filename for snapshot based on type and date"""  
    if snapshot_type == 'daily':
        date_str = date_obj.strftime('%Y-%m-%d')
        return f"{date_str}.json"
    elif snapshot_type == 'weekly':
        # ISO week format: 2025-W26
        year, week, _ = date_obj.isocalendar()
        return f"{year}-W{week:02d}.json"
    elif snapshot_type == 'monthly':
        date_str = date_obj.strftime('%Y-%m')
        return f"{date_str}.json"
    elif snapshot_type == 'quarterly':
        quarter = (date_obj.month - 1) // 3 + 1
        return f"{date_obj.year}-Q{quarter}.json"
    elif snapshot_type == 'yearly':
        return f"{date_obj.year}.json"
    else:
        return f"{date_obj.strftime('%Y-%m-%d')}.json"

def get_user_snapshots_dir(base_snapshots_dir, username):
    """
    Generate the user-specific snapshots directory path
    
    Args:
        base_snapshots_dir: The base snapshots directory
        username: The username to create a subdirectory for
        
    Returns:
        Full path to the user's snapshots directory
    """
    import os
    username_clean = username.lower().replace('@', '')
    return os.path.join(base_snapshots_dir, username_clean)

def validate_snapshots_dir(snapshots_dir):
    """
    Validate the snapshots directory path
    
    Args:
        snapshots_dir: Path to validate for snapshots storage
        
    Returns:
        Tuple of (is_valid, message, normalized_path)
    """
    import os
    
    if not snapshots_dir:
        return False, "Snapshots directory cannot be empty", None
    
    # Normalize the path (removes trailing slashes, resolves ./ and ../)
    normalized_path = os.path.normpath(snapshots_dir)
    
    # Check if path is absolute and starts with root (potential security issue)
    if os.path.isabs(normalized_path) and normalized_path in ['/', '\\', 'C:\\', 'D:\\']:
        return False, "Cannot use root directory as snapshots directory", None
    
    # Check for potentially dangerous paths
    dangerous_patterns = ['..', '~', '$']
    if any(pattern in normalized_path for pattern in dangerous_patterns):
        return False, "Path contains potentially unsafe characters", None
    
    # Try to create the directory to test writability
    try:
        os.makedirs(normalized_path, exist_ok=True)
        
        # Test write permissions with a temporary file
        test_file = os.path.join(normalized_path, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except (IOError, OSError) as e:
            return False, f"Directory is not writable: {e}", None
            
    except (IOError, OSError, PermissionError) as e:
        return False, f"Cannot create directory: {e}", None
    
    return True, "Valid snapshots directory", normalized_path
