
def read_gpg_encrypted_file(file_path):
    """Reads key from encrypted."""
    with open(file_path, 'r') as fp:
        key = fp.read() 
    return key