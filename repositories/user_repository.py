from models.user import User
from database.db_manager import DatabaseManager


def create_user(user_id: str, username: str, email: str, password: str) -> User:
    if get_user_by_id(user_id) is not None:
        raise ValueError(f"User with ID {user_id} already exists.")
    new_user = User(username=username, email=email, password=password, user_id=user_id)
    db_manager = DatabaseManager()  # Initialize the database manager
    db_manager.execute(
        "INSERT INTO users (user_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
        (new_user.user_id, new_user.username, new_user.email, new_user.password_hash),
    )
    return new_user

def authenticate_user(user_id: str, password: str) -> bool:
    db_manager = DatabaseManager()  # Initialize the database manager
    user_row = db_manager.fetch_one(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    )
    if user_row:
        stored_password_hash = user_row["password_hash"]
        user = User(username=user_row["username"], email=user_row["email"], password="", user_id=user_row["user_id"])
        user.password_hash = stored_password_hash  # Set the stored hash for verification
        return user.verify_password(password)
    return False

def get_user_by_id(user_id: str) -> User | None:
    db_manager = DatabaseManager()  # Initialize the database manager
    user_row = db_manager.fetch_one(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    )
    if user_row:
        return User(
            username=user_row["username"],
            email=user_row["email"],
            password="",  # Password is not retrieved for security reasons
            user_id=user_row["user_id"]
        )
    return None
