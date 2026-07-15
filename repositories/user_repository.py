from database.db_manager import DatabaseManager
from models.user import User

class UserRepository:
    def __init__(self, db_manager: DatabaseManager | None = None):
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            self.db_manager = DatabaseManager()

    def create_user(self, username: str, email: str, password: str) -> User:
        if self.get_by_username(username) is not None:
            raise ValueError(f"Username '{username}' is already taken.")
        new_user = User(username=username, email=email, password=password)
        cursor = self.db_manager.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (new_user.username, new_user.email, new_user.password_hash),
        )
        new_user.user_id = cursor.lastrowid
        return new_user

    def authenticate(self, user_credentials: str, password: str) -> User | None:
        if "@" in user_credentials:
            row = self.db_manager.fetch_one(
                "SELECT user_id, username, email, password_hash FROM users WHERE email = ?",
                (user_credentials,),
            )
        else:
            row = self.db_manager.fetch_one(
                "SELECT user_id, username, email, password_hash FROM users WHERE username = ?",
                (user_credentials,),
            )
        if row is None:
            return None
        user = User(username=row[1], email=row[2], password="", user_id=row[0])
        user.password_hash = row[3]
        if user.verify_password(password):
            return user
        return None

    def get_by_username(self, username: str) -> User | None:
        row = self.db_manager.fetch_one(
            "SELECT user_id, username, email FROM users WHERE username = ?",
            (username,),
        )
        if row is None:
            return None
        return User(username=row[1], email=row[2], password="", user_id=row[0])

    def get_by_id(self, user_id: int) -> User | None:
        row = self.db_manager.fetch_one(
            "SELECT user_id, username, email FROM users WHERE user_id = ?",
            (user_id,),
        )
        if row is None:
            return None
        return User(username=row[1], email=row[2], password="", user_id=row[0])
