from cryptography.fernet import Fernet

from core.config import settings


def encrypt_bytes(plaintext: bytes) -> bytes:
    return Fernet(settings.fernet_key.encode()).encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes) -> bytes:
    return Fernet(settings.fernet_key.encode()).decrypt(ciphertext)
