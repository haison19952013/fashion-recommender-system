def key_to_url(key: str) -> str:
    """
    Converts a pinterest hex key into a url.
    
    Args:
        key: Pinterest hexadecimal key (must be at least 6 characters)
        
    Returns:
        Pinterest image URL
        
    Raises:
        ValueError: If key is too short or invalid format
    """
    if not key or len(key) < 6:
        raise ValueError(f"Pinterest key must be at least 6 characters, got: {key}")
    
    if not all(c in '0123456789abcdefABCDEF' for c in key):
        raise ValueError(f"Pinterest key must be hexadecimal, got: {key}")
    
    prefix = 'https://i.pinimg.com/400x/%s/%s/%s/%s.jpg'
    return prefix % (key[0:2], key[2:4], key[4:6], key)