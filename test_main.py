import main
import unittest
import sqlite3
from unittest import mock

db_path = 'data\\db.db'


class UserTests(unittest.TestCase):
    test_telegram_id = 99999999999
    test_telegram_id_for_create = 000000000000
    test_telegram_id_for_portfolio_check = 999999999991

    def setUp(self) -> None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('create table if not exists users (telegram_id INTEGER primary key)')
        cursor.execute('''create table if not exists portfolio (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          ticker TEXT,
                          price REAL,
                          supply real,
                          r_telegram_id INTEGER,
                          FOREIGN KEY(r_telegram_id) REFERENCES users(telegram_id)
                          )''')
        cursor.execute('insert into users (telegram_id) values (?)', (self.test_telegram_id,))
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('delete from users where (telegram_id) = (?)', (self.test_telegram_id,))
        cursor.execute('delete from users where (telegram_id) = (?)', (self.test_telegram_id_for_create,))
        cursor.execute('delete from users where (telegram_id) = (?)', (self.test_telegram_id_for_portfolio_check,))
        cursor.execute('delete from portfolio where (r_telegram_id) = (?)',
                       (self.test_telegram_id_for_portfolio_check,))
        conn.commit()
        conn.close()

    def test_user_record(self):
        user = main.User(self.test_telegram_id)
        result = user.check_user_record()
        self.assertEqual(result[0], self.test_telegram_id)

    def test_create_user(self):
        user = main.User(self.test_telegram_id_for_create)
        user.create_user_record()
        result = user.check_user_record()
        self.assertEqual(result[0], self.test_telegram_id_for_create)

    def test_check_portfolio_empty(self):
        user = main.User(self.test_telegram_id)
        result = user.check_portfolio()
        self.assertEqual(result, [])

    def test_add_asset(self):
        asset = main.Asset('ASD', 100, 100, self.test_telegram_id_for_portfolio_check)
        result = asset.add_asset()
        self.assertIsNotNone(result)

    def test_check_portfolio_not_empty(self):
        user = main.User(self.test_telegram_id_for_portfolio_check)
        asset = main.Asset('ASD', 100, 100, self.test_telegram_id_for_portfolio_check)
        asset.add_asset()
        result = user.check_portfolio()
        self.assertEqual(result[0][0], float(asset.price))
        self.assertEqual(result[0][1], float(asset.price))
        self.assertEqual(result[0][2], float(asset.supply))
        self.assertEqual(result[0][3], asset.ticker)

    def test_last_added_asset(self):
        user = main.User(self.test_telegram_id_for_portfolio_check)
        asset = main.Asset('ASD', 100, 100, self.test_telegram_id_for_portfolio_check)
        asset.add_asset()
        last_added_asset = user.last_added_asset()
        self.assertEqual(last_added_asset[0], asset.ticker)
        self.assertEqual(last_added_asset[1], float(asset.price))
        self.assertEqual(last_added_asset[2], float(asset.supply))
        self.assertEqual(last_added_asset[3], self.test_telegram_id_for_portfolio_check)

    def test_check_asset_in_portfolio(self):
        user = main.User(self.test_telegram_id_for_portfolio_check)
        asset = main.Asset('ASD', 100, 100, self.test_telegram_id_for_portfolio_check)
        asset.add_asset()
        check_asset = user.check_asset_in_portfolio(asset.ticker)
        self.assertEqual(check_asset[0], asset.ticker)

    def test_check_asset_not_in_portfolio(self):
        user = main.User(self.test_telegram_id_for_portfolio_check)
        asset = main.Asset('ASD', 100, 100, self.test_telegram_id_for_portfolio_check)
        check_asset = user.check_asset_in_portfolio(asset.ticker)
        self.assertIsNone(check_asset)

    def test_delete_asset_from_portfolio(self):
        user = main.User(self.test_telegram_id_for_portfolio_check)
        asset = main.Asset('ASD', 100, 100, self.test_telegram_id_for_portfolio_check)
        asset.add_asset()
        user.delete_asset_from_portfolio(asset.ticker)
        check_asset = user.check_asset_in_portfolio(asset.ticker)
        self.assertIsNone(check_asset)


class LogicTests(unittest.TestCase):

    def test_check_connection(self):
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        test_response_asset_name = 'BTC'

        with mock.patch('requests.get') as mock_get:
            mock_response_success = mock.Mock()
            mock_response_success.status_code = 200

            mock_response_error = mock.Mock()
            mock_response_error.status_code = 400
            mock_response_error.json.return_value = None

            mock_get.return_value = mock_response_success
            result_success = main.check_connection()[0].get('symbol')
            self.assertEqual(result_success, test_response_asset_name)


if __name__ == '__main__':
    unittest.main()
