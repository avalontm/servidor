# apis/products.py
from flask import Blueprint, jsonify

products_bp = Blueprint('product', __name__)

# Ruta para ver productos
@products_bp.route('/products', methods=['GET'])
def get_products():
    # Esta es una respuesta simulada, deberías conectarla a tu base de datos
    products = [
        {"id": 1, "name": "Producto 1", "price": 10},
        {"id": 2, "name": "Producto 2", "price": 20},
    ]
    return jsonify(products)
