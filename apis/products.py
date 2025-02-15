# apis/products.py
#esta seccion esta siendo desarollada por scarleth
from flask import Blueprint, jsonify
from mysql.connector import Error
from utils.db_utils import get_db_connection

products_bp = Blueprint('product', __name__)

# Ruta para ver productos
@products_bp.route('/listar', methods=['GET'])
def obtener_productos():
    """Obtiene todos los productos de la base de datos."""
    connection = get_db_connection()

    if not connection:
        return None  # Retorna None si no hay conexión

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM productos"  # Ajusta los campos según tu BD
        cursor.execute(query)
        productos = cursor.fetchall()  # Obtiene todos los productos
        
        return jsonify(productos)  # Retorna una lista de diccionarios con los productos
    except Error as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()