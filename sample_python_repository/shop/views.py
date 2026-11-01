from shop.services import price_with_tax
from shop.models import Product

def product_detail(product_id):
    price = price_with_tax(100)
    return {'id': product_id, 'price': price}
