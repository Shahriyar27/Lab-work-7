"""SQLite: таблицы и простые операции с товарами."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name('store.db')


@contextmanager
def connect():
    # with сохраняет изменения при успехе и отменяет при ошибке.
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    first_start = not DB_PATH.exists()
    with connect() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0)
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                total_price REAL NOT NULL CHECK(total_price >= 0)
            );
        ''')
        if first_start:
            db.executemany('INSERT INTO products(name, category, price) VALUES (?, ?, ?)', [
                ('Игровая мышь', 'Мыши', 35),
                ('Игровая клавиатура', 'Клавиатуры', 75),
                ('Игровой ноутбук', 'Ноутбуки', 1200),
                ('Игровая гарнитура', 'Гарнитуры', 60),
            ])


class ProductRepository:
    """Реальный объект, который выполняет SQL. Proxy обращается к нему."""

    def list(self):
        with connect() as db:
            return db.execute('SELECT * FROM products ORDER BY id').fetchall()

    def get(self, product_id):
        with connect() as db:
            return db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

    def add(self, name, category, price):
        with connect() as db:
            db.execute('INSERT INTO products(name, category, price) VALUES (?, ?, ?)',
                       (name, category, price))

    def edit(self, product_id, name, category, price):
        with connect() as db:
            db.execute('UPDATE products SET name = ?, category = ?, price = ? WHERE id = ?',
                       (name, category, price, product_id))

    def delete(self, product_id):
        with connect() as db:
            db.execute('DELETE FROM products WHERE id = ?', (product_id,))
