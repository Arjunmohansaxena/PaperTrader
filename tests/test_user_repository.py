import os
import tempfile
import unittest
 
from database.db_manager import DatabaseManager
from repositories.user_repository import UserRepository
 
 
class UserRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "papertrader.db")
        self.db_manager = DatabaseManager(db_path)
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
        with open(schema_path) as schema_file:
            self.db_manager.executescript(schema_file.read())
        self.repository = UserRepository(self.db_manager)
 
    def tearDown(self):
        self.db_manager.close()
        self.temp_dir.cleanup()
 
    def test_create_user_assigns_an_id(self):
        user = self.repository.create_user("alice", "alice@example.com", "secret123")
        self.assertIsNotNone(user.user_id)
        self.assertEqual(user.username, "alice")
 
    def test_create_user_rejects_duplicate_username(self):
        self.repository.create_user("alice", "alice@example.com", "secret123")
        with self.assertRaises(ValueError):
            self.repository.create_user("alice", "different@example.com", "otherpass")
 
    def test_authenticate_with_correct_credentials(self):
        self.repository.create_user("alice", "alice@example.com", "secret123")
        user = self.repository.authenticate("alice", "secret123")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "alice")
 
    def test_authenticate_with_wrong_password_returns_none(self):
        self.repository.create_user("alice", "alice@example.com", "secret123")
        user = self.repository.authenticate("alice", "wrongpassword")
        self.assertIsNone(user)
 
    def test_authenticate_with_unknown_username_returns_none(self):
        user = self.repository.authenticate("nobody", "whatever")
        self.assertIsNone(user)
 
    def test_get_by_username(self):
        created = self.repository.create_user("alice", "alice@example.com", "secret123")
        found = self.repository.get_by_username("alice")
        self.assertEqual(found.user_id, created.user_id)
 
    def test_get_by_username_returns_none_when_missing(self):
        self.assertIsNone(self.repository.get_by_username("nobody"))
 
    def test_get_by_id(self):
        created = self.repository.create_user("alice", "alice@example.com", "secret123")
        found = self.repository.get_by_id(created.user_id)
        self.assertEqual(found.username, "alice")
 
    def test_get_by_id_returns_none_when_missing(self):
        self.assertIsNone(self.repository.get_by_id(9999))
 
 
if __name__ == "__main__":
    unittest.main()
 