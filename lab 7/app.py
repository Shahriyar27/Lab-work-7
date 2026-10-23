"""Запуск: python app.py. Адрес: http://127.0.0.1:5000"""
import os
import secrets
import sqlite3
import sys
import webbrowser
from functools import wraps
from threading import Timer
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from database import connect, init_db
from patterns import OrderFacade, ProductProxy, parse_price

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
USERS = {
    'admin': {'password': 'admin123', 'role': 'admin'},
    'student': {'password': 'student123', 'role': 'customer'},
}
init_db()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return function(*args, **kwargs)
    return wrapper


def product_proxy():
    return ProductProxy(session.get('role', 'customer'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = USERS.get(username)
        if user and user['password'] == request.form.get('password'):
            session.clear()
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('products'))
        flash('Неверный логин или пароль.')
    return render_template('login.html')


@app.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.get('/')
@login_required
def products():
    return render_template('products.html', products=product_proxy().list())


@app.route('/products/add', methods=['GET', 'POST'])
@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def product_form(product_id=None):
    proxy = product_proxy()
    proxy.check_permission()
    product = proxy.get(product_id) if product_id is not None else None
    if product_id is not None and product is None:
        abort(404)
    if request.method == 'POST':
        product = request.form
        try:
            name = request.form.get('name', '').strip()
            category = request.form.get('category', '').strip()
            if not name or not category:
                raise ValueError('Заполните название и категорию.')
            price = parse_price(request.form.get('price', ''))
            if product_id is None:
                proxy.add(name, category, price)
            else:
                proxy.edit(product_id, name, category, price)
            flash('Товар сохранён.')
            return redirect(url_for('products'))
        except ValueError as error:
            flash(str(error))
    return render_template('product_form.html', product=product, editing=product_id is not None)


@app.post('/products/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    proxy = product_proxy()
    proxy.check_permission()
    if proxy.get(product_id) is None:
        abort(404)
    try:
        proxy.delete(product_id)
        flash('Товар удалён.')
    except sqlite3.IntegrityError:
        flash('Этот товар уже есть в заказе. Удаление запрещено, чтобы сохранить историю.')
    return redirect(url_for('products'))


@app.post('/orders/add/<int:product_id>')
@login_required
def add_order(product_id):
    try:
        total = OrderFacade().place_order(session['username'], product_id,
                                          request.form.get('quantity', ''))
        flash(f'Заказ оформлен! Сумма: ${total:.2f}.')
        return redirect(url_for('orders'))
    except ValueError as error:
        flash(str(error))
        return redirect(url_for('products'))


@app.get('/orders')
@login_required
def orders():
    sql = '''SELECT orders.*, products.name AS product_name
             FROM orders JOIN products ON products.id = orders.product_id'''
    parameters = ()
    if session['role'] != 'admin':
        sql += ' WHERE orders.customer_name = ?'
        parameters = (session['username'],)
    with connect() as db:
        rows = db.execute(sql + ' ORDER BY orders.id DESC', parameters).fetchall()
    return render_template('orders.html', orders=rows)


@app.errorhandler(PermissionError)
def forbidden(error):
    return render_template('error.html', message=str(error)), 403


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message='Страница или товар не найдены.'), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    if '--open-browser' in sys.argv:
        Timer(1.5, lambda: webbrowser.open(f'http://127.0.0.1:{port}')).start()
    app.run(host='127.0.0.1', port=port, debug=False)
