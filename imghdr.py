# Compatibility shim for environments where stdlib `imghdr` is missing (e.g., Python 3.13)
# We don't upload local images, so a minimal stub is enough.

def what(file, h=None):
    return None
