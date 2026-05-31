from cryptography.fernet import Fernet
from src.core.config import settings

class TokenEncryption:
    def __init__(self):
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())

    # Шифрует строку и возвращает base64-строку (токен)
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    # Расшифровывает обратно в исходную строку
    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()

token_encryption = TokenEncryption()