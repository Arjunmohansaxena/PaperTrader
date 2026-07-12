import hashlib
import os


class User:
    def __init__(self, username: str, email: str, password: str):
        self.username = username
        self.email = email
        self.password_hash = self.hash_password(password)

    @staticmethod
    def hash_password(password: str) -> str:
        salt = os.urandom(16).hex()
        password_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return f"{salt}${password_hash}"

    def verify_password(self, password: str) -> bool:
        salt, stored_hash = self.password_hash.split("$", 1)
        computed_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return computed_hash == stored_hash
