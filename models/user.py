from werkzeug.security import generate_password_hash, check_password_hash


class User:
    def __init__(self, username: str, email: str, password: str, user_id: int | None = None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = self.hash_password(password)

    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password)

    def verify_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)