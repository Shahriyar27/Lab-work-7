"""Два обязательных паттерна: Proxy и Facade."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from database import ProductRepository, connect


def parse_price(value):
    try:
        price = Decimal(str(value))
        if not price.is_finite() or price < 0 or price > 1_000_000_000:
            raise ValueError
        return float(price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        raise ValueError('Цена должна быть числом от 0 до 1 000 000 000.') from None


class ProductProxy:
    """Посредник: проверяет роль, затем передаёт работу хранилищу."""

    def __init__(self, role):
        self.role = role
        self.repository = ProductRepository()

    def check_permission(self):
        if self.role != 'admin':
            raise PermissionError('Управлять товарами может только администратор.')

    def list(self):
        return self.repository.list()

    def get(self, product_id):
        return self.repository.get(product_id)

    def add(self, name, category, price):
        self.check_permission()
        self.repository.add(name, category, price)

    def edit(self, product_id, name, category, price):
        self.check_permission()
        self.repository.edit(product_id, name, category, price)

    def delete(self, product_id):
        self.check_permission()
        self.repository.delete(product_id)


class OrderFacade:
    """Один вызов объединяет проверку, расчёт и сохранение заказа."""

    def place_order(self, customer_name, product_id, quantity):
        if not customer_name.strip():
            raise ValueError('Имя покупателя не должно быть пустым.')
        try:
            quantity = int(str(quantity))
        except (ValueError, TypeError):
            raise ValueError('Количество должно быть целым числом.') from None
        if not 1 <= quantity <= 10000:
            raise ValueError('Количество должно быть от 1 до 10 000.')
        with connect() as db:
            # Цена и наличие товара берутся из базы, а не из браузера.
            product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if product is None:
                raise ValueError('Товар не найден.')
            total = (Decimal(str(product['price'])) * quantity).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
            db.execute('''INSERT INTO orders(customer_name, product_id, quantity, total_price)
                          VALUES (?, ?, ?, ?)''',
                       (customer_name.strip(), product_id, quantity, float(total)))
        return float(total)
