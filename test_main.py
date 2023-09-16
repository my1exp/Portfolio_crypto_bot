import main
import unittest
import sqlite3
from unittest import mock

db_path = 'C:\\Users\\Nikita\\IdeaProjects\\Portfolio_crypto_bot\\db.db'


class user_tests(unittest.TestCase):
    test_telegram_id = 99999999999
    test_telegram_id_for_create = 000000000000

    def setUp(self) -> None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('create table if not exists users (telegram_id INTEGER primary key)')
        cursor.execute('insert into users (telegram_id) values (?)', (self.test_telegram_id,))
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('delete from users where (telegram_id) = (?)', (self.test_telegram_id,))
        cursor.execute('delete from users where (telegram_id) = (?)', (self.test_telegram_id_for_create,))
        conn.commit()
        conn.close()

    def test_user_existence(self):
        user = main.User(self.test_telegram_id)
        result = user.check_user_record()
        self.assertEqual(result, self.test_telegram_id)

    def test_create_user(self):
        user = main.User(self.test_telegram_id_for_create)
        user.create_user_record()
        result_check = user.check_user_record()
        self.assertEqual(result_check, self.test_telegram_id_for_create)


if __name__ == '__main__':
    unittest.main()
