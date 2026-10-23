"""Подготовка страниц для снимков из настоящих шаблонов на временной базе."""
import tempfile
from pathlib import Path
import database
from app import app

output = Path(__file__).parent / 'screenshots'
output.mkdir(exist_ok=True)
css = (Path(__file__).parent / 'static/style.css').read_text(encoding='utf-8')
original = database.DB_PATH
with tempfile.TemporaryDirectory() as folder:
    database.DB_PATH = Path(folder) / 'preview.db'
    database.init_db()
    client = app.test_client()

    def save(name, response):
        html = response.get_data(as_text=True)
        html = html.replace('<link rel="stylesheet" href="/static/style.css">', f'<style>{css}</style>')
        (output / (name + '.html')).write_text(html, encoding='utf-8')

    save('01-login', client.get('/login'))
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    save('02-admin-products', client.get('/'))
    save('03-edit-product', client.get('/products/edit/1'))
    client.post('/login', data={'username': 'student', 'password': 'student123'})
    save('04-customer-products', client.get('/'))
    save('05-order', client.post('/orders/add/1', data={'quantity': '2'}, follow_redirects=True))
    save('06-access-denied', client.get('/products/add'))
database.DB_PATH = original
print('Prepared 6 rendered application pages; store.db unchanged.')
