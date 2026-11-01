from shop.models import Product

def price_with_tax(price, rate=0.18):
    if price < 0:
        raise ValueError('price cannot be negative')
    return price * (1 + rate)
