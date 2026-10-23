"""Проверка лабораторной на временной базе: настоящая store.db не меняется."""
import tempfile
import unittest
from pathlib import Path
import database
from app import app
from patterns import OrderFacade


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.original = database.DB_PATH
        database.DB_PATH = Path(self.folder.name) / 'test.db'
        database.init_db()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        database.DB_PATH = self.original
        self.folder.cleanup()

    def login(self, username):
        return self.client.post('/login', data={'username': username, 'password': username + '123'})

    def test_crud_and_persistence(self):
        self.login('admin')
        self.assertEqual(self.client.get('/').status_code, 200)
        self.client.post('/products/add', data={'name': 'Test', 'category': 'Mouse', 'price': '12.50'})
        with database.connect() as db:
            product_id = db.execute("SELECT id FROM products WHERE name = 'Test'").fetchone()[0]
        self.client.post(f'/products/edit/{product_id}', data={'name': 'Changed', 'category': 'Mouse', 'price': '20'})
        database.init_db()
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT price FROM products WHERE id = ?', (product_id,)).fetchone()[0], 20)
        self.client.post(f'/products/delete/{product_id}')
        with database.connect() as db:
            self.assertIsNone(db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone())
        self.assertEqual(self.client.get('/products/edit/99999').status_code, 404)

    def test_customer_cannot_manage_products_even_by_direct_request(self):
        self.login('student')
        for url in ['/products/add', '/products/edit/1', '/products/delete/1']:
            self.assertEqual(self.client.post(url, data={'name': 'Hack', 'category': 'X', 'price': '1'}).status_code, 403)
        self.assertEqual(self.client.get('/products/add').status_code, 403)
        self.assertEqual(self.client.get('/products/edit/1').status_code, 403)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_facade_total_visibility_and_delete_restriction(self):
        self.login('student')
        response = self.client.post('/orders/add/1', data={'quantity': '2', 'total_price': '0'}, follow_redirects=True)
        self.assertIn(b'70.00', response.data)
        OrderFacade().place_order('admin', 2, '1')
        self.assertNotIn(b'75.00', self.client.get('/orders').data)
        self.login('admin')
        self.assertIn(b'75.00', self.client.get('/orders').data)
        self.client.post('/products/delete/1')
        with database.connect() as db:
            self.assertIsNotNone(db.execute('SELECT * FROM products WHERE id = 1').fetchone())
            self.assertEqual(db.execute('SELECT total_price FROM orders WHERE id = 1').fetchone()[0], 70)

    def test_invalid_input_is_not_saved(self):
        self.login('student')
        for quantity in ['0', '-1', '1.5', 'abc', '', '10001']:
            self.client.post('/orders/add/1', data={'quantity': quantity})
        self.client.post('/orders/add/99999', data={'quantity': '1'})
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM orders').fetchone()[0], 0)
        self.login('admin')
        for price in ['-1', 'nan', 'inf', '', 'abc']:
            self.client.post('/products/add', data={'name': 'Bad', 'category': 'X', 'price': price})
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM products').fetchone()[0], 4)

    def test_login_logout(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        self.client.post('/login', data={'username': 'admin', 'password': 'wrong'})
        self.assertEqual(self.client.get('/').status_code, 302)
        self.login('admin')
        self.assertEqual(self.client.get('/products/add').status_code, 200)
        self.assertEqual(self.client.get('/products/edit/1').status_code, 200)
        self.client.post('/logout')
        self.assertEqual(self.client.get('/orders').status_code, 302)


if __name__ == '__main__':
    unittest.main(verbosity=2)
