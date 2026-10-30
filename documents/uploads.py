import hashlib

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# allowed file extensions
ALLOWED_EXTENSIONS = {
    '.pdf': 'pdf',
    '.png': 'png',
    '.jpg': 'jpg',
    '.jpeg': 'jpg',
}

# first bytes of each file type
FILE_SIGNATURES = {
    'pdf': b'%PDF-',
    'png': b'\x89PNG\r\n\x1a\n',
    'jpg': b'\xff\xd8\xff',
}

# content types used when serving a file
CONTENT_TYPES = {
    'pdf': 'application/pdf',
    'png': 'image/png',
    'jpg': 'image/jpeg',
}


# work out the real type from the first bytes
def detect_file_type(uploaded_file):
    header = uploaded_file.read(8)
    uploaded_file.seek(0)

    for file_type, signature in FILE_SIGNATURES.items():
        if header.startswith(signature):
            return file_type

    return None


# fingerprint of the file contents
def file_sha256(uploaded_file):
    digest = hashlib.sha256()

    for chunk in uploaded_file.chunks():
        digest.update(chunk)

    uploaded_file.seek(0)
    return digest.hexdigest()
