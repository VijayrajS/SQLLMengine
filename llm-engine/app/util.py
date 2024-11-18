from decimal import Decimal

def read_gpg_encrypted_file(file_path):
    """Reads key from encrypted."""
    with open(file_path, 'r') as fp:
        key = fp.read() 
    return key

def decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, list):
        return [decimal_to_float(item) for item in value]
    elif isinstance(value, tuple):
        return tuple(decimal_to_float(item) for item in value)
    elif isinstance(value, dict):
        return {key: decimal_to_float(val) for key, val in value.items()}
    return value
